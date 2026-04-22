import sys
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import os

# --- Constants & State ---
current_state = "MENU" 
selected_option = -1 
selected_rocket_index = 0
selected_rocket_for_game = 0  
rocket_selected = False  
show_alert = False  
alert_message = ""  
last_click_x, last_click_y = -1000, -1000 
animation_time = 0.0
planet_rotation_y = 0.0

# Camera Controls for 3D Viewer
cam_x, cam_y = 15.0, 0.0
zoom_level = 1.0  

main_menu = ["START GAME", "OPTIONS", "QUIT"]
options_menu = ["TUTORIAL", "CHECK ROCKET", "BACK"]
rocket_list = ["JakHound F-22 Raptor", "EvaNation F-15 Eagle", "TasroFighter JF17 Thunder", "START MISSION"]

# --- Gameplay State ---
rocket_x, rocket_y = -150.0, 25.0  # Spawn far to the left to force exploration!
vel_x, vel_y = 0.0, 0.0 
autopilot_on = False
game_status = "PLAYING" 
keys = {'UP': False, 'DOWN': False, 'LEFT': False, 'RIGHT': False}

# --- Star Setup ---
star_data = []
for _ in range(700):
    tx, ty = random.uniform(-100, 100), random.uniform(-60, 60)
    star_data.append([tx, ty, random.uniform(-150, -20), random.uniform(0.5, 0.9), tx, ty])

# --- Moon Dust Setup (Gameplay only) ---
moon_dust = []
for _ in range(150):
    moon_dust.append([random.uniform(-40, 40), random.uniform(0, 40), random.uniform(-10, 10), 
                      random.uniform(0.01, 0.03), random.uniform(0, 10)])

# --- Terrain Generator (Gameplay only - Massively Extended!) ---
def get_terrain_height(rx):
    if -4.5 <= rx <= 4.5: return 0.0  # Flat landing pad exactly at center (X=0)
    return math.sin(rx * 0.8) * 1.5 + math.cos(rx * 0.3) * 2.0 - 1.0

moon_terrain = []
# Extended terrain from -250 to 250 so you have to fly a long way
for i in range(-250, 250, 1):
    moon_terrain.append((i, get_terrain_height(i)))

# --- UI Helpers ---
def draw_bold_text(x, y, text, r, g, b):
    glColor3f(r, g, b)
    temp_x = x
    for char in text:
        glRasterPos2f(temp_x, y)
        glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(char))
        temp_x += 9

def draw_button(x, y, text, index):
    global selected_option
    text_width = len(text) * 10 
    x_start, x_end = x - (text_width / 2) - 20, x + (text_width / 2) + 20
    y_start, y_end = y - 10, y + 25
    gl_click_y = 800 - last_click_y 

    if x_start <= last_click_x <= x_end and y_start <= gl_click_y <= y_end:
        selected_option = index

    is_selected = (selected_option == index)
    if is_selected:
        draw_bold_text(x - (text_width / 2), y, text, 1.0, 1.0, 1.0)
        glColor3f(1.0, 0.2, 0.2)
        glLineWidth(3.0)
    else:
        draw_bold_text(x - (text_width / 2), y, text, 0.7, 0.1, 0.1)
        glColor3f(0.4, 0.0, 0.0)
        glLineWidth(1.0)

    glBegin(GL_LINE_LOOP)
    glVertex2f(x_start, y_start); glVertex2f(x_end, y_start)
    glVertex2f(x_end, y_end); glVertex2f(x_start, y_end)
    glEnd()
    glLineWidth(1.0)

# --- Background Scene (Restored Original Moon) ---
def draw_interactive_scene():
    glPointSize(3.0)
    glBegin(GL_POINTS)
    target_x = (last_click_x - 500) / 6.0
    target_y = (400 - last_click_y) / 6.0
    for i, s in enumerate(star_data):
        blink = 0.2 + 0.6 * abs(math.sin(animation_time * 5 + i))
        glColor3f(blink * s[3], blink * s[3], blink * s[3])
        dx, dy = target_x - s[0], target_y - s[1]
        dist = math.sqrt(dx**2 + dy**2)
        if dist < 15.0: 
            s[0] += dx * 0.05
            s[1] += dy * 0.05
        else:
            s[0] += (s[4] - s[0]) * 0.02
            s[1] += (s[5] - s[1]) * 0.02
        glVertex3f(s[0], s[1], s[2])
    glEnd()
    
    glPushMatrix()
    glTranslatef(22, -14, -45)
    tilt_x = (last_click_y - 400) / 40.0
    tilt_y = (last_click_x - 500) / 40.0
    glRotatef(planet_rotation_y + tilt_y, 0, 1, 0)
    glRotatef(tilt_x, 1, 0, 0)
    q = gluNewQuadric()
    glColor3f(0.8, 0.8, 0.82); gluSphere(q, 16, 48, 48)
    glPushMatrix(); glRotatef(animation_time * 8, 1, 1, 0) 
    glColor3f(0.3, 0.3, 0.32); gluSphere(q, 16.1, 8, 8); glPopMatrix()
    glPopMatrix()

# --- Realistic Rocket Models ---
def draw_cylinder_new(base_r, top_r, height, slices=32, stacks=4):
    q = gluNewQuadric()
    gluCylinder(q, base_r, top_r, height, slices, stacks)

def draw_sphere_new(r, slices=32, stacks=32):
    q = gluNewQuadric()
    gluSphere(q, r, slices, stacks)

def draw_disk_new(inner, outer, slices=32):
    q = gluNewQuadric()
    gluCylinder(q, outer, inner, 0.01, slices, 1)

def draw_cone_new(base, height, slices=32):
    draw_cylinder_new(base, 0.0, height, slices)

# --- ROCKET 0: EvaNation / F-15 Eagle ---
def draw_eva_nation():
    glColor3f(0.95, 0.55, 0.75)
    glPushMatrix(); glRotatef(-90, 1, 0, 0); draw_cylinder_new(0.42, 0.38, 2.2); glPopMatrix()
    glColor3f(0.97, 0.97, 0.97)
    glPushMatrix(); glTranslatef(0.0, 0.8, 0.42); glScalef(0.28, 0.70, 0.05); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.90, 0.40, 0.65)
    glPushMatrix(); glTranslatef(0.0, 2.2, 0.0); glRotatef(-90, 1, 0, 0); draw_cone_new(0.38, 1.10); glPopMatrix()
    glColor3f(0.85, 0.45, 0.70)
    glPushMatrix(); glRotatef(90, 1, 0, 0); draw_disk_new(0.0, 0.42); glPopMatrix()
    fin_cols = [(0.80, 0.35, 0.60), (0.90, 0.45, 0.70), (0.80, 0.35, 0.60), (0.90, 0.45, 0.70)]
    for i, col in enumerate(fin_cols):
        glColor3f(*col)
        glPushMatrix(); glRotatef(i * 90, 0, 1, 0); glTranslatef(0.38, 0.10, 0.0); glScalef(0.55, 0.85, 0.06); glutSolidCube(1.0); glPopMatrix()

# --- ROCKET 1: TasroFighter / JF-17 Thunder ---
def draw_jf17_thunder():
    glColor3f(0.55, 0.05, 0.05)
    glPushMatrix(); glRotatef(-90, 1, 0, 0); draw_cylinder_new(0.34, 0.30, 2.0, 6); glPopMatrix()
    glColor3f(0.65, 0.07, 0.07)
    glPushMatrix(); glTranslatef(0.0, 2.0, 0.0); glRotatef(-90, 1, 0, 0); draw_cone_new(0.30, 0.90, 6); glPopMatrix()
    glColor3f(0.45, 0.04, 0.04)
    glPushMatrix(); glRotatef(90, 1, 0, 0); draw_disk_new(0.0, 0.34, 6); glPopMatrix()
    fin_data = [(1,0,0), (-1,0,0), (0,0,1), (0,0,-1)]
    for fx, fy, fz in fin_data:
        glColor3f(0.50, 0.05, 0.05)
        glPushMatrix(); glTranslatef(fx*0.44, 0.15, fz*0.44); glScalef(0.40 if fx != 0 else 0.06, 0.70, 0.40 if fz != 0 else 0.06); glutSolidCube(1.0); glPopMatrix()
    flame = 0.5 + 0.5 * math.sin(animation_time * 8.0)
    scale_main = 0.85 + 0.30 * flame
    glColor3f(1.0, 0.4, 0.0)
    glPushMatrix(); glTranslatef(0.0, -0.2, 0.0); glRotatef(90, 1, 0, 0); draw_cone_new(0.1, 0.5 * scale_main); glPopMatrix()

# --- ROCKET 2: JakHound / F-22 Raptor ---
def draw_jak_hound():
    glColor3f(0.14, 0.14, 0.16)
    glPushMatrix(); glRotatef(-90, 1, 0, 0); draw_cylinder_new(0.32, 0.28, 2.10, 8); glPopMatrix()
    glColor3f(0.05, 0.55, 0.95)
    glPushMatrix(); glTranslatef(0.0, 1.52, 0.33); draw_sphere_new(0.09); glPopMatrix()
    glColor3f(0.18, 0.18, 0.20)
    glPushMatrix(); glTranslatef(0.0, 2.10, 0.0); glRotatef(-90, 1, 0, 0); draw_cone_new(0.28, 0.95, 8); glPopMatrix()
    glColor3f(0.12, 0.12, 0.14)
    glPushMatrix(); glRotatef(90, 1, 0, 0); draw_disk_new(0.0, 0.32, 8); glPopMatrix()
    for i in range(4):
        glColor3f(0.12, 0.12, 0.14)
        glPushMatrix(); glRotatef(i * 90, 0, 1, 0); glTranslatef(0.30, 0.10, 0.0); glScalef(0.40, 0.65, 0.05); glutSolidCube(1.0); glPopMatrix()

# --- Main Logic ---
def display():
    glClearColor(0.08, 0.08, 0.12, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    if current_state in ["MENU", "OPTIONS"]:
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45, 1.25, 0.1, 500.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity(); draw_interactive_scene()
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, 1000, 0, 800)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        active_list = main_menu if current_state == "MENU" else options_menu
        for i, option in enumerate(active_list):
            draw_button(500, 500 - (i * 90), option, i)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state == "ROCKET_LIST":
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, 1000, 0, 800)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        draw_bold_text(400, 650, "SELECT SPACECRAFT", 1, 1, 1)
        for i in range(3):
            draw_button(500, 500 - (i * 100), rocket_list[i], i)
        
        draw_button(500, 200, "START MISSION", 3)
        draw_button(150, 50, " BACK ", 99) 
        
        if show_alert:
            draw_bold_text(500, 350, alert_message, 1, 0, 0)
        
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state == "ROCKET_VIEWER":
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45, 1.25, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        glTranslatef(0, 0, -25 * zoom_level)
        glRotatef(cam_x, 1, 0, 0); glRotatef(cam_y, 0, 1, 0)
        
        if selected_rocket_index == 0: draw_jak_hound()
        elif selected_rocket_index == 1: draw_eva_nation()
        elif selected_rocket_index == 2: draw_jf17_thunder()
        
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, 1000, 0, 800)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        draw_bold_text(20, 750, f"INSPECTING: {rocket_list[selected_rocket_index]}", 1, 1, 0)
        
        if selected_rocket_for_game == selected_rocket_index:
            draw_bold_text(20, 720, "SELECTED FOR MISSION! | F: RESELECT", 0, 1, 0)
        else:
            draw_bold_text(20, 720, "PRESS F TO SELECT THIS ROCKET", 0.7, 0.7, 0.7)
        
        draw_bold_text(20, 690, "ARROWS: ROTATE | N: ZOOM IN | M: ZOOM OUT | ESC: BACK", 0.5, 0.5, 0.5)
        draw_button(150, 50, " BACK ", 99)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state == "GAMEPLAY":
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(60, 1.25, 0.1, 300.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        # CAMERA strictly follows the rocket left/right across the giant map
        cam_target_x = rocket_x 
        cam_target_y = rocket_y * 0.4
        gluLookAt(cam_target_x, cam_target_y + 12.0, 65.0, 
                  cam_target_x, cam_target_y, 0.0, 
                  0.0, 1.0, 0.0)

        # Draw Animated Moon Dust (Dynamically tracks your camera position)
        glPointSize(2.0)
        glBegin(GL_POINTS)
        for d in moon_dust:
            # Shift the dust position so it infinitely wraps around the rocket
            dust_x = rocket_x + ((d[0] - rocket_x + 40) % 80) - 40 
            glow = 0.3 + 0.7 * abs(math.sin(animation_time * 2 + d[4]))
            glColor3f(glow, glow, glow)
            glVertex3f(dust_x, d[1], d[2])
        glEnd()

        # Draw Moon Terrain
        glColor3f(0.25, 0.25, 0.3)
        glBegin(GL_QUAD_STRIP)
        for tx, ty in moon_terrain:
            glVertex3f(tx, -20.0, 0) 
            glVertex3f(tx, ty, 0)    
        glEnd()
        
        glColor3f(0.4, 0.4, 0.5)
        glLineWidth(2.0)
        glBegin(GL_LINE_STRIP)
        for tx, ty in moon_terrain:
            glVertex3f(tx, ty + 0.05, 0)
        glEnd()
        glLineWidth(1.0)

        # Draw Yellow Landing Pad (Always at X = 0)
        glColor3f(0.9, 0.8, 0.1)
        glBegin(GL_QUADS)
        glVertex3f(-4.5, 0.02, 2); glVertex3f(4.5, 0.02, 2)
        glVertex3f(4.5, 0.02, -2); glVertex3f(-4.5, 0.02, -2)
        glEnd()

        # Draw Rocket
        glPushMatrix()
        glTranslatef(rocket_x, rocket_y, 0)
        glScalef(2.0, 2.0, 2.0) 
        glRotatef(vel_x * -100.0, 0, 0, 1) 
        
        if selected_rocket_for_game == 0: draw_jak_hound()
        elif selected_rocket_for_game == 1: draw_eva_nation()
        elif selected_rocket_for_game == 2: draw_jf17_thunder()
        
        # Bottom Flame (UP arrow)
        if keys['UP']:
            glColor3f(1.0, 0.5, 0.0)
            glPushMatrix()
            glTranslatef(0, -0.5, 0); glRotatef(-90, 1, 0, 0)
            draw_cone_new(0.3, 1.5 + math.sin(animation_time*30)*0.3)
            glPopMatrix()
            
        # Top Retro-Thruster (DOWN arrow)
        if keys['DOWN']:
            glColor3f(0.3, 0.8, 1.0)
            glPushMatrix()
            glTranslatef(0, 3.2, 0); glRotatef(90, 1, 0, 0)
            draw_cone_new(0.2, 1.0 + math.sin(animation_time*30)*0.2)
            glPopMatrix()
            
        glPopMatrix()

        # HUD Overlay
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, 1000, 0, 800)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        
        # Calculate real altitude from ground
        ground_below = get_terrain_height(rocket_x)
        real_alt = max(0, rocket_y - ground_below - 4.5)
        
        draw_bold_text(20, 750, f"ALTITUDE: {real_alt:.1f}m", 1, 1, 1)
        draw_bold_text(20, 720, f"VERT SPD: {vel_y*100:.1f}", 1, 0 if vel_y < -0.3 else 1, 0)
        draw_bold_text(20, 690, f"HORZ SPD: {vel_x*100:.1f}", 1, 0 if abs(vel_x) > 0.25 else 1, 1)
        
        # Add Landing Pad Direction/Distance Tracker
        dist_to_pad = abs(rocket_x)
        direction_arrow = "->" if rocket_x < 0 else "<-"
        draw_bold_text(20, 640, f"LANDING PAD: {dist_to_pad:.0f}m {direction_arrow}", 1.0, 0.8, 0.2)

        draw_bold_text(650, 750, "[DOWN] THRUST DOWNWARDS", 0.3, 0.8, 1.0)
        draw_bold_text(650, 720, "[UP] THRUST UPWARDS", 1.0, 0.6, 0.2)
        draw_bold_text(650, 690, "[< / >] MOVE LEFT/RIGHT", 0.8, 0.8, 0.8)

        if game_status == "LANDED":
            draw_bold_text(380, 450, "SUCCESSFUL MOON LANDING!", 0, 1, 0)
            draw_bold_text(360, 420, "PRESS R TO RESTART OR ESC TO MENU", 1, 1, 1)
        elif game_status == "CRASHED":
            draw_bold_text(420, 450, "ROCKET CRASHED!", 1, 0, 0)
            draw_bold_text(360, 420, "PRESS R TO RESTART OR ESC TO MENU", 1, 1, 1)

        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    glutSwapBuffers()

# --- Inputs ---
def mouse_click(button, state, x, y):
    global current_state, selected_option, selected_rocket_index, last_click_x, last_click_y, show_alert, alert_message
    global rocket_x, rocket_y, vel_x, vel_y, game_status
    
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        last_click_x, last_click_y = x, y
        ly = 800 - y 

        if current_state == "ROCKET_LIST":
            for i in range(3):
                if 400 <= x <= 600 and (500 - (i*100) - 10) <= ly <= (500 - (i*100) + 25):
                    selected_rocket_index, current_state = i, "ROCKET_VIEWER"
            
            if 400 <= x <= 600 and 190 <= ly <= 215:
                if not rocket_selected:
                    show_alert = True
                    alert_message = "Select your Spacecraft first!!"
                else:
                    current_state = "GAMEPLAY"
                    rocket_x, rocket_y = -150.0, 25.0; vel_x, vel_y = 0.0, 0.0; game_status = "PLAYING"
            
            if x <= 250 and ly <= 100: 
                current_state = "OPTIONS"
                selected_option = 1 

        elif current_state == "ROCKET_VIEWER":
            if x <= 250 and ly <= 100: 
                current_state = "ROCKET_LIST"

        else:
            active_list = main_menu if current_state == "MENU" else options_menu
            for i, opt in enumerate(active_list):
                if 400 <= x <= 600 and (500-(i*90)-10) <= ly <= (500-(i*90)+25):
                    if selected_option == i:
                        if current_state == "MENU":
                            if i == 0: 
                                current_state = "GAMEPLAY"
                                rocket_x, rocket_y = -150.0, 25.0; vel_x, vel_y = 0.0, 0.0; game_status = "PLAYING"
                            elif i == 1: current_state = "OPTIONS"; selected_option = -1
                            elif i == 2: os._exit(0)
                        elif current_state == "OPTIONS":
                            if i == 1: current_state = "ROCKET_LIST"; selected_option = -1
                            elif i == 2: current_state = "MENU"; selected_option = 1
                    else:
                        selected_option = i
                        
    glutPostRedisplay()

def special_keys(key, x, y):
    global cam_x, cam_y, selected_option, current_state, selected_rocket_index, keys
    
    if current_state == "ROCKET_VIEWER":
        if key == GLUT_KEY_LEFT: cam_y -= 5.0
        elif key == GLUT_KEY_RIGHT: cam_y += 5.0
        elif key == GLUT_KEY_UP: cam_x -= 5.0  
        elif key == GLUT_KEY_DOWN: cam_x += 5.0  
        
    elif current_state in ["MENU", "OPTIONS", "ROCKET_LIST"]:
        menu_items = main_menu if current_state == "MENU" else (options_menu if current_state == "OPTIONS" else rocket_list)
        max_options = len(menu_items) - 1
        
        if selected_option < 0 or selected_option > max_options: selected_option = 0
        
        if key == GLUT_KEY_UP: selected_option = max(0, (selected_option - 1) % (max_options + 1))
        elif key == GLUT_KEY_DOWN: selected_option = min(max_options, (selected_option + 1) % (max_options + 1))
        
    elif current_state == "GAMEPLAY":
        if key == GLUT_KEY_UP: keys['UP'] = True
        elif key == GLUT_KEY_DOWN: keys['DOWN'] = True
        elif key == GLUT_KEY_LEFT: keys['LEFT'] = True
        elif key == GLUT_KEY_RIGHT: keys['RIGHT'] = True
    
    glutPostRedisplay()

def special_keys_up(key, x, y):
    global keys
    if key == GLUT_KEY_UP: keys['UP'] = False
    elif key == GLUT_KEY_DOWN: keys['DOWN'] = False
    elif key == GLUT_KEY_LEFT: keys['LEFT'] = False
    elif key == GLUT_KEY_RIGHT: keys['RIGHT'] = False

def keyboard(key, x, y):
    global current_state, selected_option, zoom_level, selected_rocket_index, selected_rocket_for_game
    global rocket_selected, show_alert, alert_message, keys, game_status, rocket_x, rocket_y, vel_x, vel_y
    
    if ord(key) == 27:
        if current_state == "GAMEPLAY": current_state = "MENU"
        elif current_state == "OPTIONS": current_state = "MENU"; selected_option = 1  
        elif current_state == "ROCKET_LIST": current_state = "OPTIONS"; selected_option = 1; show_alert = False  
        elif current_state == "ROCKET_VIEWER": current_state = "ROCKET_LIST"; selected_option = selected_rocket_index  
    
    if current_state in ["MENU", "OPTIONS", "ROCKET_LIST"]:
        menu_items = main_menu if current_state == "MENU" else (options_menu if current_state == "OPTIONS" else rocket_list)
        max_options = len(menu_items) - 1
        
        if selected_option < 0 or selected_option > max_options: selected_option = 0
            
        if key == b'\r' or key == b' ':  
            if current_state == "MENU":
                if selected_option == 0: 
                    current_state = "ROCKET_LIST"
                    selected_option = selected_rocket_for_game
                elif selected_option == 1: current_state = "OPTIONS"; selected_option = -1
                elif selected_option == 2: os._exit(0)
            elif current_state == "OPTIONS":
                if selected_option == 0: pass  
                elif selected_option == 1: current_state = "ROCKET_LIST"; selected_option = -1
                elif selected_option == 2: current_state = "MENU"; selected_option = 1
            elif current_state == "ROCKET_LIST":
                if selected_option >= 0 and selected_option < 3:
                    selected_rocket_index = selected_option
                    current_state = "ROCKET_VIEWER"
                elif selected_option == 3:  
                    if not rocket_selected:
                        show_alert = True
                        alert_message = "Select your Spacecraft first!!"
                    else:
                        current_state = "GAMEPLAY"
                        rocket_x, rocket_y = -150.0, 25.0; vel_x, vel_y = 0.0, 0.0; game_status = "PLAYING"
    
    if current_state == "ROCKET_VIEWER":
        if key == b'n' or key == b'N': zoom_level = max(0.2, zoom_level - 0.1)  
        elif key == b'm' or key == b'M': zoom_level = min(3.0, zoom_level + 0.1)  
        elif key == b'f' or key == b'F':
            selected_rocket_for_game = selected_rocket_index  
            rocket_selected = True

    elif current_state == "GAMEPLAY":
        if key == b'r' or key == b'R': 
            game_status = "PLAYING"
            rocket_x, rocket_y = -150.0, 25.0
            vel_x, vel_y = 0.0, 0.0 
            
    glutPostRedisplay()

def idle():
    global animation_time, planet_rotation_y, rocket_x, rocket_y, vel_x, vel_y
    global keys, game_status, moon_dust
    
    animation_time += 0.01; planet_rotation_y += 0.015
    
    for d in moon_dust:
        d[0] += math.sin(animation_time * d[3] * 10 + d[4]) * 0.05
        d[1] += math.cos(animation_time * d[3] * 5) * 0.02
    
    if current_state == "GAMEPLAY" and game_status == "PLAYING":
        
        # ZERO GRAVITY HOVER: Removed artificial buoyancy. 
        # Rocket holds its altitude perfectly until you thrust UP or DOWN.
        
        if keys['DOWN']: vel_y -= 0.010  
        if keys['UP']: vel_y += 0.010    
        if keys['LEFT']: vel_x -= 0.006
        if keys['RIGHT']: vel_x += 0.006
            
        vel_x *= 0.96 
        vel_y *= 0.96 
        
        rocket_x += vel_x
        rocket_y += vel_y
        
        # Increased ceiling limit significantly so you don't hit an invisible roof
        if rocket_y > 150.0:
            rocket_y = 150.0
            vel_y = 0.0
        
        ground_y = get_terrain_height(rocket_x)
        rocket_bottom_offset = 4.5  
        
        if (rocket_y - rocket_bottom_offset) <= ground_y:
            rocket_y = ground_y + rocket_bottom_offset
            
            if -4.8 <= rocket_x <= 4.8 and abs(vel_y) < 0.35 and abs(vel_x) < 0.25:
                game_status = "LANDED"
            else:
                game_status = "CRASHED"
                
            vel_x, vel_y = 0, 0
            keys['UP'], keys['DOWN'] = False, False

    glutPostRedisplay()

def main():
    glutInit(sys.argv) 
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutCreateWindow(b"Lunar Descent")
    
    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutMouseFunc(mouse_click)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutSpecialUpFunc(special_keys_up)
    
    glEnable(GL_DEPTH_TEST)
    glutMainLoop()

if __name__ == "__main__": 
    main()
    