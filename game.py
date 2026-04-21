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
selected_rocket_for_game = 0  # Rocket selected for gameplay
rocket_selected = False  # Flag to check if a rocket was selected for game
show_alert = False  # Alert message flag
alert_message = ""  # Alert message text
last_click_x, last_click_y = -1000, -1000 
animation_time = 0.0
planet_rotation_y = 0.0

# Camera Controls for 3D Viewer
cam_x, cam_y = 15.0, 0.0
zoom_level = 1.0  # Zoom level for rocket viewer

main_menu = ["START GAME", "OPTIONS", "QUIT"]
options_menu = ["TUTORIAL", "CHECK ROCKET", "BACK"]
rocket_list = ["JakHound F-22 Raptor", "EvaNation F-15 Eagle", "TasroFighter JF17 Thunder", "START MISSION"]

# --- Star Setup ---
star_data = []
for _ in range(700):
    tx, ty = random.uniform(-100, 100), random.uniform(-60, 60)
    star_data.append([tx, ty, random.uniform(-150, -20), random.uniform(0.5, 0.9), tx, ty])

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

# --- Background Scene ---
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
    glColor3f(0.8, 0.8, 0.82); gluSphere(q, 16, 48, 48) # Realistic moon color
    glPushMatrix(); glRotatef(animation_time * 8, 1, 1, 0) 
    glColor3f(0.3, 0.3, 0.32); gluSphere(q, 16.1, 8, 8); glPopMatrix()
    glPopMatrix()

# --- Realistic Rocket Models (Manual Shading) ---
# Helper functions for new rocket designs
def draw_cylinder_new(base_r, top_r, height, slices=32, stacks=4):
    q = gluNewQuadric()
    gluCylinder(q, base_r, top_r, height, slices, stacks)

def draw_sphere_new(r, slices=32, stacks=32):
    q = gluNewQuadric()
    gluSphere(q, r, slices, stacks)

def draw_disk_new(inner, outer, slices=32):
    # Use cylinder with 0 top radius as alternative to gluDisk
    q = gluNewQuadric()
    gluCylinder(q, outer, inner, 0.01, slices, 1)

def draw_cone_new(base, height, slices=32):
    draw_cylinder_new(base, 0.0, height, slices)

# --- ROCKET 0: EvaNation / F-15 Eagle (Pink chrome) ---
def draw_eva_nation():
    # Body (wide pink cylinder)
    glColor3f(0.95, 0.55, 0.75)
    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    draw_cylinder_new(0.42, 0.38, 2.2)
    glPopMatrix()

    # Glossy white cockpit window panel
    glColor3f(0.97, 0.97, 0.97)
    glPushMatrix()
    glTranslatef(0.0, 0.8, 0.42)
    glScalef(0.28, 0.70, 0.05)
    glutSolidCube(1.0)
    glPopMatrix()

    # Window panel gold trim lines
    glColor3f(0.85, 0.72, 0.30)
    for yw in [0.5, 0.9, 1.30]:
        glPushMatrix()
        glTranslatef(0.0, yw, 0.42)
        glScalef(0.30, 0.04, 0.06)
        glutSolidCube(1.0)
        glPopMatrix()

    # Nose cone
    glColor3f(0.90, 0.40, 0.65)
    glPushMatrix()
    glTranslatef(0.0, 2.2, 0.0)
    glRotatef(-90, 1, 0, 0)
    draw_cone_new(0.38, 1.10)
    glPopMatrix()

    # Nose tip highlight
    glColor3f(1.0, 0.80, 0.90)
    glPushMatrix()
    glTranslatef(0.0, 3.20, 0.0)
    draw_sphere_new(0.08)
    glPopMatrix()

    # Bottom cap
    glColor3f(0.85, 0.45, 0.70)
    glPushMatrix()
    glRotatef(90, 1, 0, 0)
    draw_disk_new(0.0, 0.42)
    glPopMatrix()

    # Wide swept fins (4 fins)
    fin_cols = [(0.80, 0.35, 0.60), (0.90, 0.45, 0.70),
                (0.80, 0.35, 0.60), (0.90, 0.45, 0.70)]
    for i, col in enumerate(fin_cols):
        glColor3f(*col)
        glPushMatrix()
        glRotatef(i * 90, 0, 1, 0)
        glTranslatef(0.38, 0.10, 0.0)
        glScalef(0.55, 0.85, 0.06)
        glutSolidCube(1.0)
        glPopMatrix()

    # Engine nozzles (3)
    nozzle_positions = [(-0.16, 0, 0), (0.16, 0, 0), (0, 0, 0)]
    for nx, ny, nz in nozzle_positions:
        glColor3f(0.60, 0.25, 0.50)
        glPushMatrix()
        glTranslatef(nx, -0.05, nz)
        glRotatef(90, 1, 0, 0)
        draw_cylinder_new(0.10, 0.08, 0.25)
        glPopMatrix()

    # Chrome side stripes
    glColor3f(1.0, 0.85, 0.92)
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.40, 1.10, 0.0)
        glScalef(0.06, 1.20, 0.06)
        glutSolidCube(1.0)
        glPopMatrix()

    # Purple accent glow ring
    glColor3f(0.55, 0.15, 0.80)
    glPushMatrix()
    glTranslatef(0.0, 0.05, 0.0)
    glRotatef(90, 1, 0, 0)
    draw_cylinder_new(0.44, 0.44, 0.05, 48)
    glPopMatrix()

# --- ROCKET 1: TasroFighter / JF-17 Thunder (Red with flames) ---
def draw_jf17_thunder():
    # Main body (angular dark red)
    glColor3f(0.55, 0.05, 0.05)
    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    draw_cylinder_new(0.34, 0.30, 2.0, 6)
    glPopMatrix()

    # Armour panel overlays
    panels = [
        (0.0,  1.50, 0.33,  0.24, 0.30, 0.05),
        (0.0,  0.90, 0.33,  0.22, 0.28, 0.05),
        (0.0,  0.35, 0.33,  0.22, 0.28, 0.05),
    ]
    glColor3f(0.70, 0.08, 0.08)
    for px, py, pz, sx, sy, sz in panels:
        glPushMatrix()
        glTranslatef(px, py, pz)
        glScalef(sx, sy, sz)
        glutSolidCube(1.0)
        glPopMatrix()

    # Red glow accent lines
    glColor3f(1.0, 0.20, 0.05)
    for yy in [0.20, 0.60, 1.00, 1.40, 1.80]:
        glPushMatrix()
        glTranslatef(0.0, yy, 0.31)
        glScalef(0.30, 0.03, 0.04)
        glutSolidCube(1.0)
        glPopMatrix()

    # Nose cone
    glColor3f(0.65, 0.07, 0.07)
    glPushMatrix()
    glTranslatef(0.0, 2.0, 0.0)
    glRotatef(-90, 1, 0, 0)
    draw_cone_new(0.30, 0.90, 6)
    glPopMatrix()

    # Nose tip bright
    glColor3f(0.9, 0.3, 0.3)
    glPushMatrix()
    glTranslatef(0.0, 2.82, 0.0)
    draw_sphere_new(0.06)
    glPopMatrix()

    # Bottom cap
    glColor3f(0.45, 0.04, 0.04)
    glPushMatrix()
    glRotatef(90, 1, 0, 0)
    draw_disk_new(0.0, 0.34, 6)
    glPopMatrix()

    # Battle fins (4, thick angular)
    fin_data = [(1,0,0), (-1,0,0), (0,0,1), (0,0,-1)]
    for fx, fy, fz in fin_data:
        glColor3f(0.50, 0.05, 0.05)
        glPushMatrix()
        glTranslatef(fx*0.44, 0.15, fz*0.44)
        glScalef(0.40 if fx != 0 else 0.06, 0.70, 0.40 if fz != 0 else 0.06)
        glutSolidCube(1.0)
        glPopMatrix()

    # Side engine pods
    for sx in [-1, 1]:
        glColor3f(0.40, 0.04, 0.04)
        glPushMatrix()
        glTranslatef(sx * 0.46, 0.30, 0.0)
        glRotatef(-90, 1, 0, 0)
        draw_cylinder_new(0.10, 0.08, 0.60)
        glPopMatrix()

    # Main engine nozzle cluster
    for nx, nz in [(0,0), (-0.18, 0), (0.18, 0), (0, -0.18), (0, 0.18)]:
        glColor3f(0.30, 0.03, 0.03)
        glPushMatrix()
        glTranslatef(nx, -0.05, nz)
        glRotatef(90, 1, 0, 0)
        draw_cylinder_new(0.075, 0.065, 0.22)
        glPopMatrix()

    # FLAMES (animated based on animation_time)
    flame = 0.5 + 0.5 * math.sin(animation_time * 8.0)
    scale_main = 0.85 + 0.30 * flame
    





# --- ROCKET 2: JakHound / F-22 Raptor (Matte black, gold trim) ---
def draw_jak_hound():
    # Main body
    glColor3f(0.14, 0.14, 0.16)
    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    draw_cylinder_new(0.32, 0.28, 2.10, 8)
    glPopMatrix()

    # Gold band (orange-gold stripe)
    glColor3f(0.85, 0.60, 0.10)
    glPushMatrix()
    glTranslatef(0.0, 1.65, 0.0)
    glRotatef(-90, 1, 0, 0)
    draw_cylinder_new(0.305, 0.295, 0.22, 8)
    glPopMatrix()

    # Blue sensor / porthole
    glColor3f(0.05, 0.55, 0.95)
    glPushMatrix()
    glTranslatef(0.0, 1.52, 0.33)
    draw_sphere_new(0.09)
    glPopMatrix()

    # Sensor glow ring
    glColor3f(0.10, 0.70, 1.0)
    glPushMatrix()
    glTranslatef(0.0, 1.52, 0.30)
    glRotatef(90, 0, 1, 0)
    draw_cylinder_new(0.10, 0.10, 0.02, 24)
    glPopMatrix()

    # Panel lines (gold)
    glColor3f(0.75, 0.55, 0.08)
    panel_ys = [0.30, 0.65, 1.00, 1.35]
    for py in panel_ys:
        glPushMatrix()
        glTranslatef(0.0, py, 0.29)
        glScalef(0.34, 0.025, 0.04)
        glutSolidCube(1.0)
        glPopMatrix()

    # Side panel recesses
    glColor3f(0.10, 0.10, 0.12)
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.18, 0.80, 0.28)
        glScalef(0.16, 0.55, 0.04)
        glutSolidCube(1.0)
        glPopMatrix()

    # Gold vertical trim lines
    glColor3f(0.80, 0.58, 0.10)
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.29, 1.00, 0.0)
        glScalef(0.04, 1.60, 0.04)
        glutSolidCube(1.0)
        glPopMatrix()

    # Nose cone (tapered, dark)
    glColor3f(0.18, 0.18, 0.20)
    glPushMatrix()
    glTranslatef(0.0, 2.10, 0.0)
    glRotatef(-90, 1, 0, 0)
    draw_cone_new(0.28, 0.95, 8)
    glPopMatrix()

    # Nose cap (gold tip)
    glColor3f(0.80, 0.60, 0.10)
    glPushMatrix()
    glTranslatef(0.0, 2.97, 0.0)
    draw_sphere_new(0.07)
    glPopMatrix()

    # Bottom cap
    glColor3f(0.12, 0.12, 0.14)
    glPushMatrix()
    glRotatef(90, 1, 0, 0)
    draw_disk_new(0.0, 0.32, 8)
    glPopMatrix()

    # Fins (4 swept, military)
    for i in range(4):
        glColor3f(0.12, 0.12, 0.14)
        glPushMatrix()
        glRotatef(i * 90, 0, 1, 0)
        glTranslatef(0.30, 0.10, 0.0)
        glScalef(0.40, 0.65, 0.05)
        glutSolidCube(1.0)
        glPopMatrix()
        # Gold fin edge
        glColor3f(0.75, 0.55, 0.08)
        glPushMatrix()
        glRotatef(i * 90, 0, 1, 0)
        glTranslatef(0.50, 0.10, 0.0)
        glScalef(0.04, 0.65, 0.055)
        glutSolidCube(1.0)
        glPopMatrix()

    # Engine nozzle (single, large)
    glColor3f(0.20, 0.20, 0.22)
    glPushMatrix()
    glTranslatef(0.0, -0.05, 0.0)
    glRotatef(90, 1, 0, 0)
    draw_cylinder_new(0.20, 0.17, 0.28, 8)
    glPopMatrix()

    # Nozzle inner dark
    glColor3f(0.08, 0.08, 0.10)
    glPushMatrix()
    glTranslatef(0.0, -0.05, 0.0)
    glRotatef(90, 1, 0, 0)
    draw_cylinder_new(0.15, 0.12, 0.28, 8)
    glPopMatrix()

    # Gold nozzle ring
    glColor3f(0.75, 0.55, 0.08)
    glPushMatrix()
    glTranslatef(0.0, -0.02, 0.0)
    glRotatef(90, 1, 0, 0)
    draw_cylinder_new(0.21, 0.21, 0.04, 8)
    glPopMatrix()

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
        # Show only the 3 rockets (not START MISSION)
        for i in range(3):
            draw_button(500, 500 - (i * 100), rocket_list[i], i)
        
        # Start Mission button
        draw_button(500, 200, "START MISSION", 3)
        
        # Navigation Button: Back to Options
        draw_button(150, 50, " BACK ", 99) 
        
        # Show alert if no rocket selected
        if show_alert:
            draw_bold_text(500, 350, alert_message, 1, 0, 0)
        
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state == "ROCKET_VIEWER":
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45, 1.25, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        # Center rocket and apply zoom
        glTranslatef(0, 0, -25 * zoom_level)
        glRotatef(cam_x, 1, 0, 0); glRotatef(cam_y, 0, 1, 0)
        
        if selected_rocket_index == 0: draw_jak_hound()
        elif selected_rocket_index == 1: draw_eva_nation()
        elif selected_rocket_index == 2: draw_jf17_thunder()
        
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, 1000, 0, 800)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        draw_bold_text(20, 750, f"INSPECTING: {rocket_list[selected_rocket_index]}", 1, 1, 0)
        
        # Show selection status
        if selected_rocket_for_game == selected_rocket_index:
            draw_bold_text(20, 720, "SELECTED FOR MISSION! | F: RESELECT", 0, 1, 0)
        else:
            draw_bold_text(20, 720, "PRESS F TO SELECT THIS ROCKET", 0.7, 0.7, 0.7)
        
        draw_bold_text(20, 690, "ARROWS: ROTATE | N: ZOOM IN | M: ZOOM OUT | ESC: BACK", 0.5, 0.5, 0.5)
        draw_button(150, 50, " BACK ", 99)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state == "GAMEPLAY":
        draw_bold_text(420, 400, f"MISSION START - {rocket_list[selected_rocket_for_game]}", 0, 1, 0)
        draw_bold_text(20, 50, "PRESS ESC TO RETURN TO MENU", 1, 1, 1)
        
    glutSwapBuffers()

def special_keys(key, x, y):
    global cam_x, cam_y, selected_option, current_state, selected_rocket_index
    
    if current_state == "ROCKET_VIEWER":
        # Arrow keys rotate the rocket (original behavior)
        if key == GLUT_KEY_LEFT:
            cam_y -= 5.0
        elif key == GLUT_KEY_RIGHT:
            cam_y += 5.0
        elif key == GLUT_KEY_UP:
            cam_x -= 5.0  # Show top of rocket
        elif key == GLUT_KEY_DOWN:
            cam_x += 5.0  # Show bottom of rocket
    elif current_state in ["MENU", "OPTIONS", "ROCKET_LIST"]:
        # Menu navigation with arrow keys
        menu_items = main_menu if current_state == "MENU" else (options_menu if current_state == "OPTIONS" else rocket_list)
        max_options = len(menu_items) - 1
        
        # Ensure selected_option is valid (not negative)
        if selected_option < 0 or selected_option > max_options:
            selected_option = 0
        
        if key == GLUT_KEY_UP:
            selected_option = max(0, (selected_option - 1) % (max_options + 1))
        elif key == GLUT_KEY_DOWN:
            selected_option = min(max_options, (selected_option + 1) % (max_options + 1))
    
    glutPostRedisplay()

def mouse_click(button, state, x, y):
    global current_state, selected_option, selected_rocket_index, last_click_x, last_click_y
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        last_click_x, last_click_y = x, y
        ly = 800 - y 

        if current_state == "ROCKET_LIST":
            for i in range(3):
                if 400 <= x <= 600 and (500 - (i*100) - 10) <= ly <= (500 - (i*100) + 25):
                    selected_rocket_index, current_state = i, "ROCKET_VIEWER"
            ````````````````
            # Start Mission button
            if 400 <= x <= 600 and 190 <= ly <= 215:
                if not rocket_selected:
                    show_alert = True
                    alert_message = "Select your Spacecraft first!!"
                else:
                    current_state = "GAMEPLAY"
            
            if x <= 250 and ly <= 100: # Back Button
                current_state = "OPTIONS"
                selected_option = 1 

        elif current_state == "ROCKET_VIEWER":
            if x <= 250 and ly <= 100: # Back Button
                current_state = "ROCKET_LIST"

        else:
            active_list = main_menu if current_state == "MENU" else options_menu
            for i, opt in enumerate(active_list):
                if 400 <= x <= 600 and (500-(i*90)-10) <= ly <= (500-(i*90)+25):
                    if selected_option == i:
                        if current_state == "MENU":
                            if i == 0: current_state = "GAMEPLAY"
                            elif i == 1: current_state = "OPTIONS"; selected_option = -1
                            elif i == 2: os._exit(0)
                        elif current_state == "OPTIONS":
                            if i == 1: current_state = "ROCKET_LIST"; selected_option = -1
                            elif i == 2: current_state = "MENU"; selected_option = 1
                    else:
                        selected_option = i
                        
    glutPostRedisplay()
def keyboard(key, x, y):
    global current_state, selected_option, zoom_level, selected_rocket_index, selected_rocket_for_game, rocket_selected, show_alert, alert_message
    
    # ASCII 27 is the Escape key
    if ord(key) == 27:
        if current_state == "GAMEPLAY":
            current_state = "MENU"
        elif current_state == "OPTIONS":
            current_state = "MENU"
            selected_option = 1  # Highlights 'OPTIONS' in the main menu
        elif current_state == "ROCKET_LIST":
            current_state = "OPTIONS"
            selected_option = 1  # Highlights 'CHECK ROCKET' in options
            show_alert = False  # Clear alert
        elif current_state == "ROCKET_VIEWER":
            current_state = "ROCKET_LIST"
            selected_option = selected_rocket_index  # Sync selection with current rocket
    
    # Menu navigation with arrow keys
    if current_state in ["MENU", "OPTIONS", "ROCKET_LIST"]:
        menu_items = main_menu if current_state == "MENU" else (options_menu if current_state == "OPTIONS" else rocket_list)
        max_options = len(menu_items) - 1
        
        # Ensure selected_option is valid (not negative)
        if selected_option < 0 or selected_option > max_options:
            selected_option = 0
            
        if key == b'\r' or key == b' ':  # Enter or Space to select
            if current_state == "MENU":
                if selected_option == 0: current_state = "ROCKET_LIST"; selected_option = selected_rocket_for_game
                elif selected_option == 1: current_state = "OPTIONS"; selected_option = -1
                elif selected_option == 2: os._exit(0)
            elif current_state == "OPTIONS":
                if selected_option == 0: pass  # Tutorial (not implemented)
                elif selected_option == 1: current_state = "ROCKET_LIST"; selected_option = -1
                elif selected_option == 2: current_state = "MENU"; selected_option = 1
            elif current_state == "ROCKET_LIST":
                if selected_option >= 0 and selected_option < 3:
                    selected_rocket_index = selected_option
                    current_state = "ROCKET_VIEWER"
                elif selected_option == 3:  # Start mission from rocket list
                    if not rocket_selected:
                        show_alert = True
                        alert_message = "Select your Spacecraft first!!"
                    else:
                        current_state = "GAMEPLAY"
    
    # Zoom controls for rocket viewer
    if current_state == "ROCKET_VIEWER":
        if key == b'n' or key == b'N':
            zoom_level = max(0.2, zoom_level - 0.1)  # Zoom in
        elif key == b'm' or key == b'M':
            zoom_level = min(3.0, zoom_level + 0.1)  # Zoom out
        elif key == b'f' or key == b'F':
            selected_rocket_for_game = selected_rocket_index  # Select this rocket for game
            rocket_selected = True
            
    glutPostRedisplay()
def idle():
    global animation_time, planet_rotation_y
    animation_time += 0.01; planet_rotation_y += 0.015
    glutPostRedisplay()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutCreateWindow(b"Lunar Descent")
    
    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutMouseFunc(mouse_click)
    
    # --- ADD THIS LINE BELOW ---
    glutKeyboardFunc(keyboard) 
    # ---------------------------
    
    glutSpecialFunc(special_keys) # This is for your arrows
    glutMainLoop()
if __name__ == "__main__": main()