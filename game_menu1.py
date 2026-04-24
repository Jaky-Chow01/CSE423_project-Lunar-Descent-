from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import os

# ─────────────────────────────────────────────
#  CONSTANTS & SHARED STATE
# ─────────────────────────────────────────────
WIN_W, WIN_H = 1000, 800

current_state = "MENU"
selected_option = -1
selected_rocket_index = 0
selected_rocket_for_game = -1
rocket_selected = False
show_alert = False
alert_message = ""
last_click_x, last_click_y = -1000, -1000
animation_time = 0.0
planet_rotation_y = 0.0

# Camera (menu viewer)
cam_x, cam_y = 15.0, 0.0
zoom_level = 1.0

main_menu    = ["START GAME", "OPTIONS", "QUIT"]
options_menu = ["TUTORIAL", "CHECK ROCKET", "BACK"]
rocket_list  = ["JakHound F-22 Raptor", "EvaNation F-15 Eagle",
                "TasroFighter JF17 Thunder", "START MISSION"]

# ─────────────────────────────────────────────
#  GAMEPLAY STATE
# ─────────────────────────────────────────────
# Lander physics
lander_x      = 0.0
lander_y      = 60.0
lander_z      = 0.0
vel_x         = 0.0
vel_y         = 0.0
vel_z         = 0.0
fuel          = 100.0
oxygen        = 100.0
game_started  = False   # stays False until first key pressed
game_over     = False
landing_msg   = ""

GRAVITY       = -0.008
THRUST_UP     = 0.045
THRUST_HORIZ  = 0.025
FUEL_BURN     = 0.18
OXY_BURN      = 0.08
FUEL_REGEN    = 0.04
LAND_VEL_MAX  = 30

# Keys held down (shared state – both mouse & keyboard update these)
key_w = False
key_a = False
key_d = False

# Camera (gameplay) – orbit around lander
gp_cam_yaw   = 0.0    # degrees, arrow left/right
gp_cam_pitch = 20.0   # degrees, arrow up/down
gp_cam_dist  = 35.0

# Landing sites  [cx, cz, radius, unlocked]
landing_sites = [
    [0.0,   0.0,  6.0, True ],
    [40.0,  20.0, 4.5, True ],
    [-35.0, 15.0, 3.5, False],
    [20.0, -40.0, 2.5, False],
]
sites_landed = 0   # how many successfully landed

# Terrain geometry (generated once)
terrain_cubes = []   # list of (x, y, z, sx, sy, sz, r, g, b)

def generate_terrain():
    global terrain_cubes
    terrain_cubes = []
    random.seed(42)
    # Flat base plane – large slabs
    for gx in range(-10, 11):
        for gz in range(-10, 11):
            x = gx * 12.0
            z = gz * 12.0
            h = random.uniform(0.5, 2.5)
            grey = random.uniform(0.30, 0.55)
            terrain_cubes.append((x, -h/2 - 1.0, z, 11.8, h, 11.8, grey, grey, grey*1.05))
    # Rocky outcrops
    for _ in range(80):
        x = random.uniform(-110, 110)
        z = random.uniform(-110, 110)
        # Keep landing sites clear
        too_close = any(math.sqrt((x-s[0])**2+(z-s[1])**2) < s[2]+4 for s in landing_sites)
        if too_close:
            continue
        sx = random.uniform(1.0, 5.0)
        sy = random.uniform(1.5, 8.0)
        sz = random.uniform(1.0, 5.0)
        grey = random.uniform(0.25, 0.50)
        terrain_cubes.append((x, sy/2, z, sx, sy, sz, grey, grey, grey*1.1))

generate_terrain()

# ─────────────────────────────────────────────
#  STARS (menu)
# ─────────────────────────────────────────────
star_data = []
for _ in range(700):
    tx, ty = random.uniform(-100, 100), random.uniform(-60, 60)
    star_data.append([tx, ty, random.uniform(-150, -20), random.uniform(0.5, 0.9), tx, ty])

# ─────────────────────────────────────────────
#  UI HELPERS
# ─────────────────────────────────────────────
def draw_text(x, y, text, r, g, b, font=GLUT_BITMAP_9_BY_15):
    glColor3f(r, g, b)
    tx = x
    for ch in text:
        glRasterPos2f(tx, y)
        glutBitmapCharacter(font, ord(ch))
        tx += 9

def draw_button(x, y, text, index):
    global selected_option
    tw = len(text) * 10
    x0, x1 = x - tw/2 - 20, x + tw/2 + 20
    y0, y1 = y - 10, y + 25
    gl_y = WIN_H - last_click_y
    if x0 <= last_click_x <= x1 and y0 <= gl_y <= y1:
        selected_option = index
    sel = (selected_option == index)
    if sel:
        draw_text(x - tw/2, y, text, 1.0, 1.0, 1.0)
        glColor3f(1.0, 0.2, 0.2); glLineWidth(3.0)
    else:
        draw_text(x - tw/2, y, text, 0.7, 0.1, 0.1)
        glColor3f(0.4, 0.0, 0.0); glLineWidth(1.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x0,y0); glVertex2f(x1,y0)
    glVertex2f(x1,y1); glVertex2f(x0,y1)
    glEnd()
    glLineWidth(1.0)

# ─────────────────────────────────────────────
#  MENU BACKGROUND
# ─────────────────────────────────────────────
def draw_interactive_scene():
    glPointSize(3.0)
    glBegin(GL_POINTS)
    tx = (last_click_x - 500) / 6.0
    ty = (400 - last_click_y) / 6.0
    for i, s in enumerate(star_data):
        blink = 0.2 + 0.6 * abs(math.sin(animation_time * 5 + i))
        glColor3f(blink*s[3], blink*s[3], blink*s[3])
        dx, dy = tx - s[0], ty - s[1]
        dist = math.sqrt(dx**2 + dy**2)
        if dist < 15.0:
            s[0] += dx * 0.05; s[1] += dy * 0.05
        else:
            s[0] += (s[4]-s[0])*0.02; s[1] += (s[5]-s[1])*0.02
        glVertex3f(s[0], s[1], s[2])
    glEnd()
    glPushMatrix()
    glTranslatef(22, -14, -45)
    glRotatef(planet_rotation_y + (last_click_x-500)/40.0, 0,1,0)
    glRotatef((last_click_y-400)/40.0, 1,0,0)
    q = gluNewQuadric()
    glColor3f(0.8, 0.8, 0.82); gluSphere(q, 16, 48, 48)
    glPushMatrix(); glRotatef(animation_time*8, 1,1,0)
    glColor3f(0.3,0.3,0.32); gluSphere(q,16.1,8,8); glPopMatrix()
    glPopMatrix()

# ─────────────────────────────────────────────
#  ROCKET MODEL HELPERS
# ─────────────────────────────────────────────
def draw_cylinder_new(br, tr, h, sl=32, st=4):
    gluCylinder(gluNewQuadric(), br, tr, h, sl, st)

def draw_sphere_new(r, sl=32, st=32):
    gluSphere(gluNewQuadric(), r, sl, st)

def draw_disk_new(inner, outer, sl=32):
    gluCylinder(gluNewQuadric(), outer, inner, 0.01, sl, 1)

def draw_cone_new(base, h, sl=32):
    draw_cylinder_new(base, 0.0, h, sl)

# ─────────────────────────────────────────────
#  ROCKET MODELS
# ─────────────────────────────────────────────
def draw_eva_nation():
    glColor3f(0.95,0.55,0.75)
    glPushMatrix(); glRotatef(-90,1,0,0); draw_cylinder_new(0.42,0.38,2.2); glPopMatrix()
    glColor3f(0.97,0.97,0.97)
    glPushMatrix(); glTranslatef(0,0.8,0.42); glScalef(0.28,0.70,0.05); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.85,0.72,0.30)
    for yw in [0.5,0.9,1.30]:
        glPushMatrix(); glTranslatef(0,yw,0.42); glScalef(0.30,0.04,0.06); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.90,0.40,0.65)
    glPushMatrix(); glTranslatef(0,2.2,0); glRotatef(-90,1,0,0); draw_cone_new(0.38,1.10); glPopMatrix()
    glColor3f(1.0,0.80,0.90)
    glPushMatrix(); glTranslatef(0,3.20,0); draw_sphere_new(0.08); glPopMatrix()
    glColor3f(0.85,0.45,0.70)
    glPushMatrix(); glRotatef(90,1,0,0); draw_disk_new(0.0,0.42); glPopMatrix()
    fin_cols=[(0.80,0.35,0.60),(0.90,0.45,0.70),(0.80,0.35,0.60),(0.90,0.45,0.70)]
    for i,col in enumerate(fin_cols):
        glColor3f(*col); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.38,0.10,0); glScalef(0.55,0.85,0.06); glutSolidCube(1.0); glPopMatrix()
    for nx,ny,nz in [(-0.16,0,0),(0.16,0,0),(0,0,0)]:
        glColor3f(0.60,0.25,0.50); glPushMatrix(); glTranslatef(nx,-0.05,nz)
        glRotatef(90,1,0,0); draw_cylinder_new(0.10,0.08,0.25); glPopMatrix()
    glColor3f(1.0,0.85,0.92)
    for side in [-1,1]:
        glPushMatrix(); glTranslatef(side*0.40,1.10,0); glScalef(0.06,1.20,0.06); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.55,0.15,0.80)
    glPushMatrix(); glTranslatef(0,0.05,0); glRotatef(90,1,0,0); draw_cylinder_new(0.44,0.44,0.05,48); glPopMatrix()

def draw_jf17_thunder():
    glColor3f(0.55,0.05,0.05)
    glPushMatrix(); glRotatef(-90,1,0,0); draw_cylinder_new(0.34,0.30,2.0,6); glPopMatrix()
    panels=[(0,1.50,0.33,0.24,0.30,0.05),(0,0.90,0.33,0.22,0.28,0.05),(0,0.35,0.33,0.22,0.28,0.05)]
    glColor3f(0.70,0.08,0.08)
    for px,py,pz,sx,sy,sz in panels:
        glPushMatrix(); glTranslatef(px,py,pz); glScalef(sx,sy,sz); glutSolidCube(1.0); glPopMatrix()
    glColor3f(1.0,0.20,0.05)
    for yy in [0.20,0.60,1.00,1.40,1.80]:
        glPushMatrix(); glTranslatef(0,yy,0.31); glScalef(0.30,0.03,0.04); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.65,0.07,0.07)
    glPushMatrix(); glTranslatef(0,2.0,0); glRotatef(-90,1,0,0); draw_cone_new(0.30,0.90,6); glPopMatrix()
    glColor3f(0.9,0.3,0.3)
    glPushMatrix(); glTranslatef(0,2.82,0); draw_sphere_new(0.06); glPopMatrix()
    glColor3f(0.45,0.04,0.04)
    glPushMatrix(); glRotatef(90,1,0,0); draw_disk_new(0.0,0.34,6); glPopMatrix()
    for fx,fy,fz in [(1,0,0),(-1,0,0),(0,0,1),(0,0,-1)]:
        glColor3f(0.50,0.05,0.05); glPushMatrix()
        glTranslatef(fx*0.44,0.15,fz*0.44)
        glScalef(0.40 if fx!=0 else 0.06, 0.70, 0.40 if fz!=0 else 0.06)
        glutSolidCube(1.0); glPopMatrix()
    for sx in [-1,1]:
        glColor3f(0.40,0.04,0.04); glPushMatrix(); glTranslatef(sx*0.46,0.30,0)
        glRotatef(-90,1,0,0); draw_cylinder_new(0.10,0.08,0.60); glPopMatrix()
    for nx,nz in [(0,0),(-0.18,0),(0.18,0),(0,-0.18),(0,0.18)]:
        glColor3f(0.30,0.03,0.03); glPushMatrix(); glTranslatef(nx,-0.05,nz)
        glRotatef(90,1,0,0); draw_cylinder_new(0.075,0.065,0.22); glPopMatrix()
    # animated flame
    flame = 0.5 + 0.5*math.sin(animation_time*8.0)
    glColor3f(1.0, 0.4+0.3*flame, 0.0)
    glPushMatrix(); glTranslatef(0,-0.05,0); glRotatef(90,1,0,0)
    draw_cone_new(0.15, 0.5+0.4*flame, 12); glPopMatrix()

def draw_jak_hound():
    glColor3f(0.14,0.14,0.16)
    glPushMatrix(); glRotatef(-90,1,0,0); draw_cylinder_new(0.32,0.28,2.10,8); glPopMatrix()
    glColor3f(0.85,0.60,0.10)
    glPushMatrix(); glTranslatef(0,1.65,0); glRotatef(-90,1,0,0); draw_cylinder_new(0.305,0.295,0.22,8); glPopMatrix()
    glColor3f(0.05,0.55,0.95)
    glPushMatrix(); glTranslatef(0,1.52,0.33); draw_sphere_new(0.09); glPopMatrix()
    glColor3f(0.10,0.70,1.0)
    glPushMatrix(); glTranslatef(0,1.52,0.30); glRotatef(90,0,1,0); draw_cylinder_new(0.10,0.10,0.02,24); glPopMatrix()
    glColor3f(0.75,0.55,0.08)
    for py in [0.30,0.65,1.00,1.35]:
        glPushMatrix(); glTranslatef(0,py,0.29); glScalef(0.34,0.025,0.04); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.10,0.10,0.12)
    for side in [-1,1]:
        glPushMatrix(); glTranslatef(side*0.18,0.80,0.28); glScalef(0.16,0.55,0.04); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.80,0.58,0.10)
    for side in [-1,1]:
        glPushMatrix(); glTranslatef(side*0.29,1.00,0); glScalef(0.04,1.60,0.04); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.18,0.18,0.20)
    glPushMatrix(); glTranslatef(0,2.10,0); glRotatef(-90,1,0,0); draw_cone_new(0.28,0.95,8); glPopMatrix()
    glColor3f(0.80,0.60,0.10)
    glPushMatrix(); glTranslatef(0,2.97,0); draw_sphere_new(0.07); glPopMatrix()
    glColor3f(0.12,0.12,0.14)
    glPushMatrix(); glRotatef(90,1,0,0); draw_disk_new(0.0,0.32,8); glPopMatrix()
    for i in range(4):
        glColor3f(0.12,0.12,0.14); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.30,0.10,0); glScalef(0.40,0.65,0.05); glutSolidCube(1.0); glPopMatrix()
        glColor3f(0.75,0.55,0.08); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.50,0.10,0); glScalef(0.04,0.65,0.055); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.20,0.20,0.22)
    glPushMatrix(); glTranslatef(0,-0.05,0); glRotatef(90,1,0,0); draw_cylinder_new(0.20,0.17,0.28,8); glPopMatrix()
    glColor3f(0.08,0.08,0.10)
    glPushMatrix(); glTranslatef(0,-0.05,0); glRotatef(90,1,0,0); draw_cylinder_new(0.15,0.12,0.28,8); glPopMatrix()
    glColor3f(0.75,0.55,0.08)
    glPushMatrix(); glTranslatef(0,-0.02,0); glRotatef(90,1,0,0); draw_cylinder_new(0.21,0.21,0.04,8); glPopMatrix()

def draw_selected_rocket():
    if   selected_rocket_for_game == 0: draw_jak_hound()
    elif selected_rocket_for_game == 1: draw_eva_nation()
    elif selected_rocket_for_game == 2: draw_jf17_thunder()
    else: draw_jak_hound()

# ─────────────────────────────────────────────
#  GAMEPLAY – TERRAIN
# ─────────────────────────────────────────────
def draw_terrain():
    for (x,y,z,sx,sy,sz,r,g,b) in terrain_cubes:
        glColor3f(r,g,b)
        glPushMatrix()
        glTranslatef(x,y,z)
        glScalef(sx,sy,sz)
        glutSolidCube(1.0)
        glPopMatrix()

# ─────────────────────────────────────────────
#  GAMEPLAY – LANDING SITES
# ─────────────────────────────────────────────
def draw_landing_sites():
    for i,(cx,cz,radius,unlocked) in enumerate(landing_sites):
        if not unlocked:
            continue
        # Draw circle on the ground using GL_LINE_LOOP
        glColor3f(0.0, 1.0, 0.3)
        glBegin(GL_LINE_LOOP)
        steps = 48
        for s in range(steps):
            angle = 2*math.pi * s / steps
            glVertex3f(cx + radius*math.cos(angle), 0.05, cz + radius*math.sin(angle))
        glEnd()
        # Inner cross marker
        glColor3f(0.0, 0.8, 0.2)
        glBegin(GL_LINES)
        glVertex3f(cx-1.5, 0.05, cz);  glVertex3f(cx+1.5, 0.05, cz)
        glVertex3f(cx, 0.05, cz-1.5);  glVertex3f(cx, 0.05, cz+1.5)
        glEnd()

# ─────────────────────────────────────────────
#  GAMEPLAY – BACKGROUND (rotating solar system)
# ─────────────────────────────────────────────
def draw_space_background():
    q = gluNewQuadric()
    # Distant stars as points
    glPointSize(2.0)
    glBegin(GL_POINTS)
    random.seed(7)
    for _ in range(500):
        angle = random.uniform(0, 2*math.pi)
        elev  = random.uniform(-math.pi/2, math.pi/2)
        dist  = 350.0
        glColor3f(random.uniform(0.6,1.0), random.uniform(0.6,1.0), random.uniform(0.7,1.0))
        glVertex3f(dist*math.cos(elev)*math.cos(angle),
                   dist*math.sin(elev),
                   dist*math.cos(elev)*math.sin(angle))
    glEnd()

    # Sun (far away)
    glPushMatrix()
    glRotatef(planet_rotation_y*0.1, 0,1,0)
    glTranslatef(300, 80, 0)
    glColor3f(1.0, 0.9, 0.3)
    gluSphere(q, 18, 24, 24)
    glPopMatrix()

    # Earth
    glPushMatrix()
    glRotatef(planet_rotation_y*0.3, 0,1,0)
    glTranslatef(200, 30, -100)
    glColor3f(0.1, 0.4, 0.8)
    gluSphere(q, 10, 24, 24)
    # clouds
    glColor3f(0.9,0.9,0.9)
    glPushMatrix(); glRotatef(planet_rotation_y*2, 0,1,0); gluSphere(q,10.2,8,8); glPopMatrix()
    glPopMatrix()

    # Mars
    glPushMatrix()
    glRotatef(planet_rotation_y*0.2, 0,1,0)
    glTranslatef(-180, -20, 150)
    glColor3f(0.7, 0.25, 0.1)
    gluSphere(q, 6, 20, 20)
    glPopMatrix()

# ─────────────────────────────────────────────
#  GAMEPLAY – THRUST FLAME
# ─────────────────────────────────────────────
def draw_thrust_flame():
    if not key_w or fuel <= 0:
        return
    flame = 0.5 + 0.5*math.sin(animation_time*15.0)
    glColor3f(1.0, 0.5+0.3*flame, 0.0)
    glPushMatrix()
    glTranslatef(0, -0.5, 0)
    glRotatef(90, 1, 0, 0)
    draw_cone_new(0.3, 1.2+0.8*flame, 12)
    glPopMatrix()

# ─────────────────────────────────────────────
#  GAMEPLAY – TRAJECTORY ARROW
# ─────────────────────────────────────────────
def draw_trajectory():
    # Predict ~60 steps ahead
    px, py, pz = lander_x, lander_y, lander_z
    vx, vy, vz = vel_x, vel_y, vel_z
    glColor3f(1.0, 1.0, 0.0)
    glBegin(GL_LINE_STRIP)
    glVertex3f(px, py, pz)
    for _ in range(60):
        vy += GRAVITY
        px += vx; py += vy; pz += vz
        if py <= 0:
            py = 0
            break
        glVertex3f(px, py, pz)
    glEnd()
    # Arrowhead at impact
    glBegin(GL_LINES)
    glVertex3f(px, py+0.5, pz)
    glVertex3f(px-0.5, py+2.0, pz)
    glVertex3f(px, py+0.5, pz)
    glVertex3f(px+0.5, py+2.0, pz)
    glEnd()

# ─────────────────────────────────────────────
#  GAMEPLAY – HUD (ortho overlay)
# ─────────────────────────────────────────────
def draw_hud():
    speed = math.sqrt(vel_x**2 + vel_y**2 + vel_z**2) * 60  # approx units/s

    # Switch to 2D ortho
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glDisable(GL_DEPTH_TEST)

    # ── Fuel bar ──
    draw_text(20, WIN_H-30, f"FUEL:   {fuel:05.1f}%", 0.2, 0.8, 0.2)
    glColor3f(0.1, 0.5, 0.1)
    glBegin(GL_QUADS)
    glVertex2f(110, WIN_H-45); glVertex2f(110+fuel*1.5, WIN_H-45)
    glVertex2f(110+fuel*1.5, WIN_H-32); glVertex2f(110, WIN_H-32)
    glEnd()

    # ── Oxygen bar ──
    draw_text(20, WIN_H-60, f"OXYGEN: {oxygen:05.1f}%", 0.2, 0.6, 1.0)
    glColor3f(0.1, 0.3, 0.7)
    glBegin(GL_QUADS)
    glVertex2f(110, WIN_H-75); glVertex2f(110+oxygen*1.5, WIN_H-75)
    glVertex2f(110+oxygen*1.5, WIN_H-62); glVertex2f(110, WIN_H-62)
    glEnd()

    # ── Speed ──
    col = (0.0,1.0,0.0) if speed <= LAND_VEL_MAX else (1.0,0.3,0.1)
    draw_text(20, WIN_H-90, f"SPEED:  {speed:05.1f} u/s", *col)

    # ── Altitude ──
    draw_text(20, WIN_H-120, f"ALT:    {max(0,lander_y):05.1f} m", 0.9, 0.9, 0.9)

    # ── Controls ──
    draw_text(20, 60, "W: THRUST  A/D: STRAFE  ARROWS: CAMERA  ESC: MENU", 0.5,0.5,0.5)

    # ── Game over message ──
    if game_over and landing_msg:
        col = (0.0,1.0,0.3) if "Perfect" in landing_msg else (1.0,0.2,0.1)
        draw_text(WIN_W//2 - len(landing_msg)*5, WIN_H//2, landing_msg, *col)
        draw_text(WIN_W//2 - 100, WIN_H//2 - 30, "PRESS R TO RESTART  |  ESC TO MENU", 0.8,0.8,0.8)

    # ── Not started yet ──
    if not game_started and not game_over:
        draw_text(WIN_W//2 - 130, WIN_H//2 - 30,
                  "PRESS W / A / D TO BEGIN MISSION", 0.9, 0.9, 0.2)

    glEnable(GL_DEPTH_TEST)
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# ─────────────────────────────────────────────
#  GAMEPLAY – MINI-MAP (top-right viewport)
# ─────────────────────────────────────────────
def draw_minimap():
    MAP_W, MAP_H = 180, 180
    MAP_X = WIN_W - MAP_W - 10
    MAP_Y = WIN_H - MAP_H - 10

    glViewport(MAP_X, MAP_Y, MAP_W, MAP_H)

    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(-120, 120, -120, 120)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glDisable(GL_DEPTH_TEST)

    # Background
    glColor3f(0.05, 0.05, 0.10)
    glBegin(GL_QUADS)
    glVertex2f(-120,-120); glVertex2f(120,-120)
    glVertex2f(120,120);   glVertex2f(-120,120)
    glEnd()

    # Border
    glColor3f(0.3,0.3,0.5)
    glBegin(GL_LINE_LOOP)
    glVertex2f(-120,-120); glVertex2f(120,-120)
    glVertex2f(120,120);   glVertex2f(-120,120)
    glEnd()

    # Landing sites
    for cx,cz,radius,unlocked in landing_sites:
        if not unlocked: continue
        glColor3f(0.0,1.0,0.3)
        glBegin(GL_LINE_LOOP)
        for s in range(24):
            a = 2*math.pi*s/24
            glVertex2f(cx+radius*math.cos(a), cz+radius*math.sin(a))
        glEnd()

    # Lander dot
    glColor3f(1.0, 1.0, 0.0)
    glPointSize(6.0)
    glBegin(GL_POINTS)
    glVertex2f(lander_x, lander_z)
    glEnd()
    glPointSize(1.0)

    # Label
    glColor3f(0.6,0.6,0.8)
    draw_text(-115, 108, "MAP", 0.6,0.6,0.8)

    glEnable(GL_DEPTH_TEST)
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    # Restore full viewport
    glViewport(0, 0, WIN_W, WIN_H)

# ─────────────────────────────────────────────
#  GAMEPLAY – PHYSICS UPDATE
# ─────────────────────────────────────────────
def update_physics():
    global lander_x, lander_y, lander_z
    global vel_x, vel_y, vel_z
    global fuel, oxygen, game_over, landing_msg, sites_landed

    if game_over or not game_started:
        return

    # Gravity always
    vel_y += GRAVITY

    # Thrust W
    if key_w:
        if fuel > 0:
            vel_y += THRUST_UP
            fuel = max(0, fuel - FUEL_BURN)
        elif oxygen > 0:
            vel_y += THRUST_UP * 0.6   # weaker on oxygen
            oxygen = max(0, oxygen - OXY_BURN)
            fuel   = min(100, fuel + FUEL_REGEN)

    # Horizontal A/D
    if key_a:
        vel_x -= THRUST_HORIZ
        if fuel > 0: fuel = max(0, fuel - FUEL_BURN*0.5)
    if key_d:
        vel_x += THRUST_HORIZ
        if fuel > 0: fuel = max(0, fuel - FUEL_BURN*0.5)

    # Damping (moon has no air, but small damping for playability)
    vel_x *= 0.99
    vel_z *= 0.99

    lander_x += vel_x
    lander_y += vel_y
    lander_z += vel_z

    # ── Ground collision ──
    if lander_y <= 0.5:
        lander_y = 0.5
        speed = math.sqrt(vel_x**2 + vel_y**2 + vel_z**2) * 60

        # Check landing site
        on_site = False
        for i,(cx,cz,radius,unlocked) in enumerate(landing_sites):
            if unlocked and math.sqrt((lander_x-cx)**2+(lander_z-cz)**2) <= radius:
                on_site = True
                if speed <= LAND_VEL_MAX and (fuel > 0 or oxygen > 0):
                    landing_msg = f"PERFECT LANDING! Speed: {speed:.1f} u/s"
                    sites_landed += 1
                    # Unlock next site & shrink it
                    for j in range(len(landing_sites)):
                        if not landing_sites[j][3]:
                            landing_sites[j][3] = True
                            landing_sites[j][2] *= 0.75
                            break
                else:
                    landing_msg = f"CRASHED! Speed: {speed:.1f} u/s  (need <= {LAND_VEL_MAX})"
                break

        if not on_site:
            landing_msg = f"CRASHED on terrain! Speed: {speed:.1f} u/s"

        game_over = True
        vel_x = vel_y = vel_z = 0

# ─────────────────────────────────────────────
#  RESET GAME
# ─────────────────────────────────────────────
def reset_game():
    global lander_x, lander_y, lander_z, vel_x, vel_y, vel_z
    global fuel, oxygen, game_started, game_over, landing_msg
    global gp_cam_yaw, gp_cam_pitch
    lander_x = lander_z = 0.0
    lander_y = 60.0
    vel_x = vel_y = vel_z = 0.0
    fuel = oxygen = 100.0
    game_started = False
    game_over    = False
    landing_msg  = ""
    gp_cam_yaw   = 0.0
    gp_cam_pitch = 20.0

# ─────────────────────────────────────────────
#  DISPLAY
# ─────────────────────────────────────────────
def display():
    glClearColor(0.04, 0.04, 0.08, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    # ── MENU / OPTIONS ──
    if current_state in ["MENU", "OPTIONS"]:
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45,1.25,0.1,500.0)
        glMatrixMode(GL_MODELVIEW);  glLoadIdentity(); draw_interactive_scene()
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,WIN_W,0,WIN_H)
        glMatrixMode(GL_MODELVIEW);  glPushMatrix(); glLoadIdentity()
        active = main_menu if current_state=="MENU" else options_menu
        for i,opt in enumerate(active):
            draw_button(500, 500-(i*90), opt, i)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    # ── ROCKET LIST ──
    elif current_state == "ROCKET_LIST":
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,WIN_W,0,WIN_H)
        glMatrixMode(GL_MODELVIEW);  glPushMatrix(); glLoadIdentity()
        draw_text(400,650,"SELECT SPACECRAFT",1,1,1)
        for i in range(3):
            draw_button(500,500-(i*100),rocket_list[i],i)
        draw_button(500,200,"START MISSION",3)
        draw_button(150,50," BACK ",99)
        if show_alert:
            draw_text(500,350,alert_message,1,0,0)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    # ── ROCKET VIEWER ──
    elif current_state == "ROCKET_VIEWER":
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45,1.25,0.1,100.0)
        glMatrixMode(GL_MODELVIEW);  glLoadIdentity()
        glTranslatef(0,0,-25*zoom_level)
        glRotatef(cam_x,1,0,0); glRotatef(cam_y,0,1,0)
        if   selected_rocket_index==0: draw_jak_hound()
        elif selected_rocket_index==1: draw_eva_nation()
        elif selected_rocket_index==2: draw_jf17_thunder()
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,WIN_W,0,WIN_H)
        glMatrixMode(GL_MODELVIEW);  glPushMatrix(); glLoadIdentity()
        draw_text(20,750,f"INSPECTING: {rocket_list[selected_rocket_index]}",1,1,0)
        if selected_rocket_for_game == selected_rocket_index:
            draw_text(20,720,"SELECTED FOR MISSION! | F: RESELECT",0,1,0)
        else:
            draw_text(20,720,"PRESS F TO SELECT THIS ROCKET",0.7,0.7,0.7)
        draw_text(20,690,"ARROWS: ROTATE | N: ZOOM IN | M: ZOOM OUT | ESC: BACK",0.5,0.5,0.5)
        draw_button(150,50," BACK ",99)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    # ── GAMEPLAY ──
    elif current_state == "GAMEPLAY":
        update_physics()

        # 3-D perspective with gluLookAt orbiting lander
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(55, WIN_W/WIN_H, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()

        # Camera position from yaw/pitch around lander
        yaw_r   = math.radians(gp_cam_yaw)
        pitch_r = math.radians(gp_cam_pitch)
        cx = lander_x + gp_cam_dist * math.cos(pitch_r) * math.sin(yaw_r)
        cy = lander_y + gp_cam_dist * math.sin(pitch_r)
        cz = lander_z + gp_cam_dist * math.cos(pitch_r) * math.cos(yaw_r)
        gluLookAt(cx,cy,cz,  lander_x,lander_y,lander_z,  0,1,0)

        # Scene
        draw_space_background()
        draw_terrain()
        draw_landing_sites()
        if not game_over:
            draw_trajectory()

        # Lander
        glPushMatrix()
        glTranslatef(lander_x, lander_y, lander_z)
        glScalef(1.5, 1.5, 1.5)
        draw_selected_rocket()
        draw_thrust_flame()
        glPopMatrix()

        # HUD overlay
        draw_hud()
        draw_minimap()

    glutSwapBuffers()

# ─────────────────────────────────────────────
#  INPUT – KEYBOARD (regular)
# ─────────────────────────────────────────────
def keyboard(key, x, y):
    global current_state, selected_option, zoom_level
    global selected_rocket_index, selected_rocket_for_game
    global rocket_selected, show_alert, alert_message
    global key_w, key_a, key_d, game_started

    k = key.lower()

    # ── ESC ──
    if ord(key) == 27:
        if current_state == "GAMEPLAY":
            current_state = "MENU"; reset_game()
        elif current_state == "OPTIONS":
            current_state = "MENU"; selected_option = 1
        elif current_state == "ROCKET_LIST":
            current_state = "OPTIONS"; selected_option = 1; show_alert = False
        elif current_state == "ROCKET_VIEWER":
            current_state = "ROCKET_LIST"; selected_option = selected_rocket_index
        glutPostRedisplay(); return

    # ── GAMEPLAY keys ──
    if current_state == "GAMEPLAY":
        if k == b'w':
            key_w = True
            if not game_started: game_started = True
        if k == b'a':
            key_a = True
            if not game_started: game_started = True
        if k == b'd':
            key_d = True
            if not game_started: game_started = True
        if k == b'r':
            reset_game()
        glutPostRedisplay(); return

    # ── Menu navigation ──
    if current_state in ["MENU","OPTIONS","ROCKET_LIST"]:
        menu_items = (main_menu if current_state=="MENU"
                      else options_menu if current_state=="OPTIONS"
                      else rocket_list)
        max_opt = len(menu_items)-1
        if selected_option < 0 or selected_option > max_opt:
            selected_option = 0

        if key in (b'\r', b' '):
            if current_state == "MENU":
                if selected_option==0: current_state="ROCKET_LIST"; selected_option=selected_rocket_for_game
                elif selected_option==1: current_state="OPTIONS"; selected_option=-1
                elif selected_option==2: os._exit(0)
            elif current_state == "OPTIONS":
                if selected_option==1: current_state="ROCKET_LIST"; selected_option=-1
                elif selected_option==2: current_state="MENU"; selected_option=1
            elif current_state == "ROCKET_LIST":
                if 0 <= selected_option < 3:
                    selected_rocket_index = selected_option
                    current_state = "ROCKET_VIEWER"
                elif selected_option == 3:
                    if not rocket_selected:
                        show_alert = True; alert_message = "Select your Spacecraft first!!"
                    else:
                        reset_game(); current_state = "GAMEPLAY"

    # ── Rocket viewer ──
    if current_state == "ROCKET_VIEWER":
        if k == b'n': zoom_level = max(0.2, zoom_level-0.1)
        elif k == b'm': zoom_level = min(3.0, zoom_level+0.1)
        elif k == b'f':
            selected_rocket_for_game = selected_rocket_index
            rocket_selected = True

    glutPostRedisplay()

def keyboard_up(key, x, y):
    global key_w, key_a, key_d
    k = key.lower()
    if k == b'w': key_w = False
    if k == b'a': key_a = False
    if k == b'd': key_d = False
    glutPostRedisplay()

# ─────────────────────────────────────────────
#  INPUT – SPECIAL KEYS (arrows)
# ─────────────────────────────────────────────
def special_keys(key, x, y):
    global cam_x, cam_y, selected_option
    global gp_cam_yaw, gp_cam_pitch

    if current_state == "GAMEPLAY":
        if key == GLUT_KEY_LEFT:  gp_cam_yaw   -= 5.0
        elif key == GLUT_KEY_RIGHT: gp_cam_yaw  += 5.0
        elif key == GLUT_KEY_UP:   gp_cam_pitch = min(85, gp_cam_pitch+3.0)
        elif key == GLUT_KEY_DOWN: gp_cam_pitch = max(-10, gp_cam_pitch-3.0)

    elif current_state == "ROCKET_VIEWER":
        if key == GLUT_KEY_LEFT:  cam_y -= 5.0
        elif key == GLUT_KEY_RIGHT: cam_y += 5.0
        elif key == GLUT_KEY_UP:   cam_x -= 5.0
        elif key == GLUT_KEY_DOWN: cam_x += 5.0

    elif current_state in ["MENU","OPTIONS","ROCKET_LIST"]:
        menu_items = (main_menu if current_state=="MENU"
                      else options_menu if current_state=="OPTIONS"
                      else rocket_list)
        max_opt = len(menu_items)-1
        if selected_option < 0: selected_option = 0
        if key == GLUT_KEY_UP:   selected_option = max(0, selected_option-1)
        elif key == GLUT_KEY_DOWN: selected_option = min(max_opt, selected_option+1)

    glutPostRedisplay()

# ─────────────────────────────────────────────
#  INPUT – MOUSE  (shares state, no focus lock)
# ─────────────────────────────────────────────
def mouse_click(button, state, x, y):
    global current_state, selected_option, selected_rocket_index
    global last_click_x, last_click_y, rocket_selected, show_alert, alert_message

    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        last_click_x, last_click_y = x, y   # shared state updated
        ly = WIN_H - y

        if current_state == "ROCKET_LIST":
            for i in range(3):
                if 400<=x<=600 and (500-(i*100)-10)<=ly<=(500-(i*100)+25):
                    selected_rocket_index = i
                    current_state = "ROCKET_VIEWER"
            if 400<=x<=600 and 190<=ly<=225:
                if not rocket_selected:
                    show_alert = True; alert_message = "Select your Spacecraft first!!"
                else:
                    reset_game(); current_state = "GAMEPLAY"
            if x<=250 and ly<=100:
                current_state = "OPTIONS"; selected_option = 1

        elif current_state == "ROCKET_VIEWER":
            if x<=250 and ly<=100:
                current_state = "ROCKET_LIST"

        else:
            active = main_menu if current_state=="MENU" else options_menu
            for i,opt in enumerate(active):
                if 400<=x<=600 and (500-(i*90)-10)<=ly<=(500-(i*90)+25):
                    if selected_option == i:   # second click = confirm
                        if current_state == "MENU":
                            if i==0: current_state="ROCKET_LIST"; selected_option=selected_rocket_for_game
                            elif i==1: current_state="OPTIONS"; selected_option=-1
                            elif i==2: os._exit(0)
                        elif current_state == "OPTIONS":
                            if i==1: current_state="ROCKET_LIST"; selected_option=-1
                            elif i==2: current_state="MENU"; selected_option=1
                    else:
                        selected_option = i   # first click = highlight

    glutPostRedisplay()

# ─────────────────────────────────────────────
#  IDLE
# ─────────────────────────────────────────────
def idle():
    global animation_time, planet_rotation_y
    animation_time    += 0.01
    planet_rotation_y += 0.015
    glutPostRedisplay()

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutCreateWindow(b"Lunar Descent")

    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutMouseFunc(mouse_click)
    glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboard_up)   # key-release for smooth thrust
    glutSpecialFunc(special_keys)

    glutMainLoop()

if __name__ == "__main__":
    main()