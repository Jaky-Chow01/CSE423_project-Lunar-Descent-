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
cam_x, cam_y = 15.0, 0.0
zoom_level = 1.0
main_menu = ["START GAME", "OPTIONS", "QUIT"]
options_menu = ["TUTORIAL", "CHECK ROCKET", "BACK"]
rocket_list = ["JakHound F-22 Raptor", "EvaNation F-15 Eagle", "TasroFighter JF17 Thunder", "START MISSION"]

star_data = []
for _ in range(700):
    tx, ty = random.uniform(-100, 100), random.uniform(-60, 60)
    star_data.append([tx, ty, random.uniform(-150, -20), random.uniform(0.5, 0.9), tx, ty])

# ============================================================
# GAMEPLAY CONSTANTS
# ============================================================
GRAVITY        = -0.0018
THRUST_POWER   = 0.012
ROTATION_SPEED = 2.2
MAX_SPEED      = 0.28
LINEAR_DRAG    = 0.994
MOON_RADIUS    = 55.0
MOON_CENTER_Y  = -70.0
MOON_SURFACE_Y = MOON_CENTER_Y + MOON_RADIUS
ROCKET_SCALE   = 1.8
STAR_SEED      = 99312

rocket_x         = 0.0
rocket_y         = 0.0
rocket_vx        = 0.0
rocket_vy        = 0.0
rocket_angle     = 90.0
rocket_thrusting = False
game_landed      = False
game_crashed     = False
game_message     = ""
game_msg_timer   = 0.0
keys_held        = set()
flame_particles  = []
obstacle_rocks   = []
cam_look_x       = 0.0
cam_look_y       = 0.0
CAM_SMOOTH       = 0.06

def reset_gameplay():
    global rocket_x, rocket_y, rocket_vx, rocket_vy, rocket_angle
    global rocket_thrusting, game_landed, game_crashed, game_message, game_msg_timer
    global flame_particles, obstacle_rocks, cam_look_x, cam_look_y
    rocket_x = 0.0
    rocket_y = MOON_SURFACE_Y + 50.0
    rocket_vx = 0.0
    rocket_vy = 0.0
    rocket_angle = 90.0
    rocket_thrusting = False
    game_landed = False
    game_crashed = False
    game_message = ""
    game_msg_timer = 0.0
    flame_particles = []
    obstacle_rocks = []
    cam_look_x = rocket_x
    cam_look_y = rocket_y
    angles = [-40, -28, -18, -10, 10, 18, 28, 40, 50, -50]
    random.shuffle(angles)
    for ang in angles[:7]:
        obstacle_rocks.append({
            'angle': ang,
            'r': random.uniform(1.0, 2.2),
            'h': random.uniform(0.8, 1.8)
        })

# ============================================================
# UI HELPERS
# ============================================================
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
    x_start = x - (text_width / 2) - 20
    x_end   = x + (text_width / 2) + 20
    y_start = y - 10
    y_end   = y + 25
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
    glVertex2f(x_end,   y_end);   glVertex2f(x_start, y_end)
    glEnd()
    glLineWidth(1.0)

# ============================================================
# MENU BACKGROUND
# ============================================================
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
            s[0] += dx * 0.05; s[1] += dy * 0.05
        else:
            s[0] += (s[4] - s[0]) * 0.02; s[1] += (s[5] - s[1]) * 0.02
        glVertex3f(s[0], s[1], s[2])
    glEnd()
    glPushMatrix()
    glTranslatef(22, -14, -45)
    tilt_x = (last_click_y - 400) / 40.0
    tilt_y = (last_click_x - 500) / 40.0
    glRotatef(planet_rotation_y + tilt_y, 0, 1, 0)
    glRotatef(tilt_x, 1, 0, 0)
    q = gluNewQuadric()
    glColor3f(0.8, 0.8, 0.82)
    gluSphere(q, 16, 48, 48)
    glPushMatrix(); glRotatef(animation_time * 8, 1, 1, 0)
    glColor3f(0.3, 0.3, 0.32); gluSphere(q, 16.1, 8, 8); glPopMatrix()
    glPopMatrix()

# ============================================================
# ROCKET MODEL HELPERS
# ============================================================
def draw_cylinder_new(base_r, top_r, height, slices=32, stacks=4):
    q = gluNewQuadric(); gluCylinder(q, base_r, top_r, height, slices, stacks)

def draw_sphere_new(r, slices=32, stacks=32):
    q = gluNewQuadric(); gluSphere(q, r, slices, stacks)

def draw_disk_new(inner, outer, slices=32):
    q = gluNewQuadric(); gluCylinder(q, outer, inner, 0.01, slices, 1)

def draw_cone_new(base, height, slices=32):
    draw_cylinder_new(base, 0.0, height, slices)

# ============================================================
# ROCKET MODELS
# ============================================================
def draw_eva_nation():
    glColor3f(0.95, 0.55, 0.75)
    glPushMatrix(); glRotatef(-90, 1, 0, 0)
    draw_cylinder_new(0.42, 0.38, 2.2); glPopMatrix()
    glColor3f(0.97, 0.97, 0.97)
    glPushMatrix(); glTranslatef(0.0, 0.8, 0.42); glScalef(0.28, 0.70, 0.05)
    glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.85, 0.72, 0.30)
    for yw in [0.5, 0.9, 1.30]:
        glPushMatrix(); glTranslatef(0.0, yw, 0.42); glScalef(0.30, 0.04, 0.06)
        glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.90, 0.40, 0.65)
    glPushMatrix(); glTranslatef(0.0, 2.2, 0.0); glRotatef(-90, 1, 0, 0)
    draw_cone_new(0.38, 1.10); glPopMatrix()
    glColor3f(1.0, 0.80, 0.90)
    glPushMatrix(); glTranslatef(0.0, 3.20, 0.0); draw_sphere_new(0.08); glPopMatrix()
    glColor3f(0.85, 0.45, 0.70)
    glPushMatrix(); glRotatef(90, 1, 0, 0); draw_disk_new(0.0, 0.42); glPopMatrix()
    fin_cols = [(0.80,0.35,0.60),(0.90,0.45,0.70),(0.80,0.35,0.60),(0.90,0.45,0.70)]
    for i, col in enumerate(fin_cols):
        glColor3f(*col); glPushMatrix(); glRotatef(i*90, 0,1,0)
        glTranslatef(0.38, 0.10, 0.0); glScalef(0.55, 0.85, 0.06)
        glutSolidCube(1.0); glPopMatrix()
    for nx, ny, nz in [(-0.16,0,0),(0.16,0,0),(0,0,0)]:
        glColor3f(0.60, 0.25, 0.50)
        glPushMatrix(); glTranslatef(nx, -0.05, nz); glRotatef(90, 1, 0, 0)
        draw_cylinder_new(0.10, 0.08, 0.25); glPopMatrix()
    glColor3f(1.0, 0.85, 0.92)
    for side in [-1,1]:
        glPushMatrix(); glTranslatef(side*0.40, 1.10, 0.0); glScalef(0.06,1.20,0.06)
        glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.55, 0.15, 0.80)
    glPushMatrix(); glTranslatef(0.0, 0.05, 0.0); glRotatef(90, 1, 0, 0)
    draw_cylinder_new(0.44, 0.44, 0.05, 48); glPopMatrix()

def draw_jf17_thunder():
    glColor3f(0.55, 0.05, 0.05)
    glPushMatrix(); glRotatef(-90, 1, 0, 0)
    draw_cylinder_new(0.34, 0.30, 2.0, 6); glPopMatrix()
    panels = [(0.0,1.50,0.33,0.24,0.30,0.05),(0.0,0.90,0.33,0.22,0.28,0.05),(0.0,0.35,0.33,0.22,0.28,0.05)]
    glColor3f(0.70, 0.08, 0.08)
    for px,py,pz,sx,sy,sz in panels:
        glPushMatrix(); glTranslatef(px,py,pz); glScalef(sx,sy,sz)
        glutSolidCube(1.0); glPopMatrix()
    glColor3f(1.0, 0.20, 0.05)
    for yy in [0.20,0.60,1.00,1.40,1.80]:
        glPushMatrix(); glTranslatef(0.0, yy, 0.31); glScalef(0.30, 0.03, 0.04)
        glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.65, 0.07, 0.07)
    glPushMatrix(); glTranslatef(0.0, 2.0, 0.0); glRotatef(-90, 1, 0, 0)
    draw_cone_new(0.30, 0.90, 6); glPopMatrix()
    glColor3f(0.9, 0.3, 0.3)
    glPushMatrix(); glTranslatef(0.0, 2.82, 0.0); draw_sphere_new(0.06); glPopMatrix()
    glColor3f(0.45, 0.04, 0.04)
    glPushMatrix(); glRotatef(90, 1, 0, 0); draw_disk_new(0.0, 0.34, 6); glPopMatrix()
    for fx,fy,fz in [(1,0,0),(-1,0,0),(0,0,1),(0,0,-1)]:
        glColor3f(0.50, 0.05, 0.05)
        glPushMatrix(); glTranslatef(fx*0.44, 0.15, fz*0.44)
        glScalef(0.40 if fx!=0 else 0.06, 0.70, 0.40 if fz!=0 else 0.06)
        glutSolidCube(1.0); glPopMatrix()
    for sx in [-1, 1]:
        glColor3f(0.40, 0.04, 0.04)
        glPushMatrix(); glTranslatef(sx*0.46, 0.30, 0.0); glRotatef(-90, 1, 0, 0)
        draw_cylinder_new(0.10, 0.08, 0.60); glPopMatrix()
    for nx,nz in [(0,0),(-0.18,0),(0.18,0),(0,-0.18),(0,0.18)]:
        glColor3f(0.30, 0.03, 0.03)
        glPushMatrix(); glTranslatef(nx, -0.05, nz); glRotatef(90, 1, 0, 0)
        draw_cylinder_new(0.075, 0.065, 0.22); glPopMatrix()

def draw_jak_hound():
    glColor3f(0.14, 0.14, 0.16)
    glPushMatrix(); glRotatef(-90, 1, 0, 0)
    draw_cylinder_new(0.32, 0.28, 2.10, 8); glPopMatrix()
    glColor3f(0.85, 0.60, 0.10)
    glPushMatrix(); glTranslatef(0.0, 1.65, 0.0); glRotatef(-90, 1, 0, 0)
    draw_cylinder_new(0.305, 0.295, 0.22, 8); glPopMatrix()
    glColor3f(0.05, 0.55, 0.95)
    glPushMatrix(); glTranslatef(0.0, 1.52, 0.33); draw_sphere_new(0.09); glPopMatrix()
    glColor3f(0.10, 0.70, 1.0)
    glPushMatrix(); glTranslatef(0.0, 1.52, 0.30); glRotatef(90, 0, 1, 0)
    draw_cylinder_new(0.10, 0.10, 0.02, 24); glPopMatrix()
    glColor3f(0.75, 0.55, 0.08)
    for py in [0.30, 0.65, 1.00, 1.35]:
        glPushMatrix(); glTranslatef(0.0, py, 0.29); glScalef(0.34, 0.025, 0.04)
        glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.10, 0.10, 0.12)
    for side in [-1, 1]:
        glPushMatrix(); glTranslatef(side*0.18, 0.80, 0.28); glScalef(0.16, 0.55, 0.04)
        glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.80, 0.58, 0.10)
    for side in [-1, 1]:
        glPushMatrix(); glTranslatef(side*0.29, 1.00, 0.0); glScalef(0.04, 1.60, 0.04)
        glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.18, 0.18, 0.20)
    glPushMatrix(); glTranslatef(0.0, 2.10, 0.0); glRotatef(-90, 1, 0, 0)
    draw_cone_new(0.28, 0.95, 8); glPopMatrix()
    glColor3f(0.80, 0.60, 0.10)
    glPushMatrix(); glTranslatef(0.0, 2.97, 0.0); draw_sphere_new(0.07); glPopMatrix()
    glColor3f(0.12, 0.12, 0.14)
    glPushMatrix(); glRotatef(90, 1, 0, 0); draw_disk_new(0.0, 0.32, 8); glPopMatrix()
    for i in range(4):
        glColor3f(0.12, 0.12, 0.14)
        glPushMatrix(); glRotatef(i*90, 0, 1, 0); glTranslatef(0.30, 0.10, 0.0)
        glScalef(0.40, 0.65, 0.05); glutSolidCube(1.0); glPopMatrix()
        glColor3f(0.75, 0.55, 0.08)
        glPushMatrix(); glRotatef(i*90, 0, 1, 0); glTranslatef(0.50, 0.10, 0.0)
        glScalef(0.04, 0.65, 0.055); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.20, 0.20, 0.22)
    glPushMatrix(); glTranslatef(0.0, -0.05, 0.0); glRotatef(90, 1, 0, 0)
    draw_cylinder_new(0.20, 0.17, 0.28, 8); glPopMatrix()
    glColor3f(0.08, 0.08, 0.10)
    glPushMatrix(); glTranslatef(0.0, -0.05, 0.0); glRotatef(90, 1, 0, 0)
    draw_cylinder_new(0.15, 0.12, 0.28, 8); glPopMatrix()
    glColor3f(0.75, 0.55, 0.08)
    glPushMatrix(); glTranslatef(0.0, -0.02, 0.0); glRotatef(90, 1, 0, 0)
    draw_cylinder_new(0.21, 0.21, 0.04, 8); glPopMatrix()

# ============================================================
# GAMEPLAY SCENE FUNCTIONS  (all defined before display)
# ============================================================

def draw_deep_stars():
    glDisable(GL_DEPTH_TEST)
    # Layer A: ultra-distant (z=-800)
    glPointSize(1.0)
    glBegin(GL_POINTS)
    random.seed(STAR_SEED + 11)
    for i in range(3000):
        b  = random.uniform(0.12, 0.55)
        tk = 0.6 + 0.4 * abs(math.sin(animation_time * 0.7 + i * 1.3))
        c  = b * tk
        t  = random.random()
        if t < 0.15:   glColor3f(c * 0.7, c * 0.8, c)
        elif t < 0.25: glColor3f(c, c * 0.85, c * 0.65)
        else:          glColor3f(c, c, c)
        glVertex3f(random.uniform(-600, 600), random.uniform(-500, 500), -800)
    glEnd()
    # Layer B: mid-field (z=-550)
    glPointSize(1.5)
    glBegin(GL_POINTS)
    random.seed(STAR_SEED + 7)
    for i in range(2000):
        b  = random.uniform(0.2, 0.75)
        tk = 0.5 + 0.5 * abs(math.sin(animation_time * 1.1 + i * 1.9))
        c  = b * tk
        t  = random.random()
        if t < 0.12:   glColor3f(c * 0.65, c * 0.75, c)
        elif t < 0.22: glColor3f(c, c * 0.80, c * 0.60)
        else:          glColor3f(c, c, c)
        glVertex3f(random.uniform(-600, 600), random.uniform(-500, 500), -550)
    glEnd()
    # Layer C: Milky Way band (z=-480)
    glPointSize(1.0)
    glBegin(GL_POINTS)
    random.seed(STAR_SEED + 3)
    for i in range(2500):
        tk = 0.35 + 0.65 * abs(math.sin(animation_time * 0.8 + i * 2.1))
        b  = random.uniform(0.15, 0.50) * tk
        glColor3f(b * 0.82, b * 0.85, b)
        glVertex3f(random.uniform(-600, 600), random.gauss(0, 50), -480)
    glEnd()
    random.seed()
    glPointSize(1.0)
    glEnable(GL_DEPTH_TEST)


def draw_space_background():
    glDisable(GL_DEPTH_TEST)
    glPointSize(2.0)
    glBegin(GL_POINTS)
    random.seed(STAR_SEED)
    for i in range(2500):
        blink  = 0.5 + 0.5 * abs(math.sin(animation_time * 1.8 + i * 1.1))
        bright = random.uniform(0.3, 1.0)
        c = blink * bright
        glColor3f(c * random.uniform(0.85,1.0), c * random.uniform(0.85,1.0), c * random.uniform(0.88,1.0))
        glVertex3f(random.uniform(-200, 200), random.uniform(-180, 180), -380)
    random.seed()
    glEnd()
    glEnable(GL_DEPTH_TEST)


def draw_earth():
    glPushMatrix()
    glTranslatef(-115.0, 68.0, -340.0)
    glRotatef(animation_time * 3.5, 0, 1, 0)
    R = 20.0
    q = gluNewQuadric()
    gluQuadricNormals(q, GLU_SMOOTH)
    # Ocean
    glColor3f(0.08, 0.28, 0.68)
    gluSphere(q, R, 64, 64)
    # Continents: (lon_centre, lat_centre, lon_span, lat_span, r, g, b)
    continents = [
        ( 20,   5,  36, 60, 0.16, 0.48, 0.14),
        ( 15,  52,  24, 22, 0.18, 0.50, 0.15),
        ( 65,  40,  40, 36, 0.17, 0.46, 0.13),
        (110,  30,  40, 34, 0.17, 0.46, 0.13),
        (-100,  45, 50, 40, 0.19, 0.50, 0.14),
        ( -55, -15, 30, 50, 0.16, 0.46, 0.12),
        ( 135, -25, 28, 26, 0.20, 0.48, 0.13),
    ]
    for lon0, lat0, dlon, dlat, cr, cg, cb in continents:
        glColor3f(cr, cg, cb)
        lat1 = lat0 - dlat / 2;  lat2 = lat0 + dlat / 2
        lon1 = lon0 - dlon / 2;  lon2 = lon0 + dlon / 2
        lat_steps = max(4, int(dlat / 5))
        lon_steps = max(4, int(dlon / 5))
        for li in range(lat_steps):
            la = lat1 + (lat2 - lat1) * li / lat_steps
            lb = lat1 + (lat2 - lat1) * (li + 1) / lat_steps
            glBegin(GL_TRIANGLE_STRIP)
            for loi in range(lon_steps + 1):
                lo = lon1 + (lon2 - lon1) * loi / lon_steps
                for lat_v in [la, lb]:
                    lat_r = math.radians(lat_v)
                    lon_r = math.radians(lo)
                    nx = math.cos(lat_r) * math.sin(lon_r)
                    ny = math.sin(lat_r)
                    nz = math.cos(lat_r) * math.cos(lon_r)
                    glVertex3f((R+0.08)*nx, (R+0.08)*ny, (R+0.08)*nz)
            glEnd()
    # Polar ice caps
    for pole_sign in [1, -1]:
        glColor3f(0.88, 0.92, 0.96)
        rim_lat = pole_sign * 68
        glBegin(GL_TRIANGLE_FAN)
        cap_lat_r = math.radians(pole_sign * 88)
        glVertex3f(0, (R+0.09) * math.sin(cap_lat_r), 0)
        for a in range(0, 361, 8):
            ar    = math.radians(a)
            rim_r = math.radians(rim_lat)
            glVertex3f((R+0.09)*math.cos(rim_r)*math.sin(ar),
                       (R+0.09)*math.sin(rim_r),
                       (R+0.09)*math.cos(rim_r)*math.cos(ar))
        glEnd()
    # Cloud bands
    cloud_bands = [
        ( 20,  55, 80, 8), (-60,  30, 70, 7),
        ( 90, -10,100, 6), (-110, 60, 60, 7),
        (150, -30, 80, 6), (  0,  10, 90, 8),
    ]
    glColor3f(0.90, 0.93, 0.97)
    for clon, clat, cspan, cwidth in cloud_bands:
        lon_steps = max(6, int(cspan / 6))
        lat1c = clat - cwidth/2;  lat2c = clat + cwidth/2
        glBegin(GL_TRIANGLE_STRIP)
        for loi in range(lon_steps + 1):
            lo = clon - cspan/2 + cspan * loi / lon_steps
            for lat_v in [lat1c, lat2c]:
                lat_r = math.radians(lat_v)
                lon_r = math.radians(lo)
                nx = math.cos(lat_r) * math.sin(lon_r)
                ny = math.sin(lat_r)
                nz = math.cos(lat_r) * math.cos(lon_r)
                glVertex3f((R+0.45)*nx, (R+0.45)*ny, (R+0.45)*nz)
        glEnd()
    # Atmosphere halo
    glColor3f(0.18, 0.42, 0.88)
    atm = gluNewQuadric()
    gluSphere(atm, R + 1.3, 40, 40)
    glPopMatrix()


def draw_moon_body():
    glPushMatrix()
    glTranslatef(0.0, MOON_CENTER_Y, -12.0)
    q = gluNewQuadric()
    gluQuadricNormals(q, GLU_SMOOTH)
    glColor3f(0.74, 0.74, 0.76)
    gluSphere(q, MOON_RADIUS, 72, 72)
    crater_defs = [
        (10,22,3.0),(-14,28,2.2),(30,12,1.8),(-26,18,3.0),(4,38,1.4),
        (-20,32,2.0),(24,32,1.2),(-6,20,1.0),(35,24,2.4),(-32,10,1.6),
        (12,10,2.8),(-16,37,1.3),(-9,-6,1.8),(20,-12,2.2),(-22,-9,1.5),
        (6,-22,2.0),(-13,-20,1.2),(27,-7,1.7),(15,45,1.0),(-18,42,1.8),(40,5,1.4),
    ]
    for cx_ang, cy_ang, cr in crater_defs:
        cx_rad = math.radians(cx_ang); cy_rad = math.radians(cy_ang)
        px = MOON_RADIUS * math.sin(cx_rad) * math.cos(cy_rad)
        py = MOON_RADIUS * math.sin(cy_rad)
        pz = MOON_RADIUS * math.cos(cx_rad) * math.cos(cy_rad)
        glPushMatrix()
        glTranslatef(px*0.97, py*0.97, pz*0.97)
        glColor3f(0.52, 0.52, 0.54)
        q2 = gluNewQuadric(); gluSphere(q2, cr, 16, 16)
        glPopMatrix()
    glPopMatrix()


def draw_moon_surface_details():
    glPushMatrix()
    glTranslatef(0.0, MOON_CENTER_Y, -11.5)
    glColor3f(0.86, 0.86, 0.88)
    glBegin(GL_POLYGON)
    for a in range(-60, 61, 4):
        rad = math.radians(a)
        glVertex3f((MOON_RADIUS+0.2)*math.sin(rad), (MOON_RADIUS+0.2)*math.cos(rad), 0)
    glEnd()
    # Landing pad
    glColor3f(0.95, 0.90, 0.10)
    glBegin(GL_POLYGON)
    for a_t in range(-60, 61, 4):
        a = a_t / 10.0
        rad = math.radians(a)
        glVertex3f((MOON_RADIUS+0.55)*math.sin(rad), (MOON_RADIUS+0.55)*math.cos(rad), 0.15)
    glEnd()
    glColor3f(1.0, 0.95, 0.05)
    glLineWidth(3.0)
    glBegin(GL_LINES)
    glVertex3f(-2.5, MOON_RADIUS+0.6, 0.25); glVertex3f(2.5, MOON_RADIUS+0.6, 0.25)
    glEnd()
    glBegin(GL_LINES)
    glVertex3f(0.0, MOON_RADIUS+0.1, 0.25); glVertex3f(0.0, MOON_RADIUS+1.1, 0.25)
    glEnd()
    glLineWidth(1.0)
    # Rocks
    for rock in obstacle_rocks:
        ang_rad = math.radians(rock['angle'])
        base_x = MOON_RADIUS * math.sin(ang_rad)
        base_y = MOON_RADIUS * math.cos(ang_rad)
        glPushMatrix()
        glTranslatef(base_x, base_y, 0.15)
        glRotatef(-rock['angle'], 0, 0, 1)
        glColor3f(0.40, 0.38, 0.42)
        glBegin(GL_POLYGON)
        for a in range(0, 360, 15):
            ar = math.radians(a)
            noise = 1.0 + 0.35 * math.sin(a * 0.15 + rock['angle'])
            glVertex3f(rock['r']*noise*math.cos(ar), rock['h']*noise*abs(math.sin(ar)), 0)
        glEnd()
        glColor3f(0.62, 0.60, 0.64)
        glBegin(GL_LINE_LOOP)
        for a in range(0, 360, 15):
            ar = math.radians(a)
            noise = 1.0 + 0.35 * math.sin(a * 0.15 + rock['angle'])
            glVertex3f(rock['r']*noise*math.cos(ar), rock['h']*noise*abs(math.sin(ar)), 0.1)
        glEnd()
        glPopMatrix()
    glPopMatrix()


def spawn_flame_particles():
    nose_rad = math.radians(rocket_angle)
    # Exhaust exits from nozzle (opposite of nose direction)
    exhaust_dx = -math.sin(nose_rad)
    exhaust_dy = -math.cos(nose_rad)
    # Nozzle position = bottom of rocket
    nozzle_x = rocket_x + exhaust_dx * ROCKET_SCALE * 0.7
    nozzle_y = rocket_y + exhaust_dy * ROCKET_SCALE * 0.7
    for _ in range(6):
        speed  = random.uniform(0.18, 0.55)
        spread = random.uniform(-0.15, 0.15)
        vx = exhaust_dx * speed + spread
        vy = exhaust_dy * speed + spread
        flame_particles.append({
            'x': nozzle_x + random.uniform(-0.06, 0.06),
            'y': nozzle_y + random.uniform(-0.06, 0.06),
            'vx': vx, 'vy': vy, 'life': 1.0,
        })


def update_flame_particles():
    global flame_particles
    for p in flame_particles:
        p['x'] += p['vx']; p['y'] += p['vy']
        p['life'] -= 0.045
    flame_particles[:] = [p for p in flame_particles if p['life'] > 0]


def draw_flame_particles():
    glDisable(GL_DEPTH_TEST)
    glPointSize(8.0)
    glBegin(GL_POINTS)
    for p in flame_particles:
        l = p['life']
        glColor3f(1.0, max(0.0, l*0.75), 0.0)
        glVertex3f(p['x'], p['y'], -11.2)
    glEnd()
    glPointSize(4.5)
    glBegin(GL_POINTS)
    for p in flame_particles:
        l = p['life']
        glColor3f(1.0, 1.0, 0.6)
        glVertex3f(p['x']+random.uniform(-0.06,0.06), p['y']+random.uniform(-0.06,0.06), -11.1)
    glEnd()
    glEnable(GL_DEPTH_TEST)


def draw_gameplay_rocket():
    glPushMatrix()
    glTranslatef(rocket_x, rocket_y, -11.5)
    glRotatef(rocket_angle, 0, 0, 1)
    glScalef(ROCKET_SCALE, ROCKET_SCALE, ROCKET_SCALE)
    if   selected_rocket_for_game == 0: draw_jak_hound()
    elif selected_rocket_for_game == 1: draw_eva_nation()
    elif selected_rocket_for_game == 2: draw_jf17_thunder()
    glPopMatrix()


def draw_mini_map():
    MAP_X, MAP_Y, MAP_W, MAP_H = 830, 10, 155, 115
    glDisable(GL_DEPTH_TEST)
    glColor3f(0.0, 0.0, 0.1)
    glBegin(GL_QUADS)
    glVertex2f(MAP_X, MAP_Y); glVertex2f(MAP_X+MAP_W, MAP_Y)
    glVertex2f(MAP_X+MAP_W, MAP_Y+MAP_H); glVertex2f(MAP_X, MAP_Y+MAP_H)
    glEnd()
    glColor3f(0.2, 0.4, 0.8)
    glBegin(GL_LINE_LOOP)
    glVertex2f(MAP_X, MAP_Y); glVertex2f(MAP_X+MAP_W, MAP_Y)
    glVertex2f(MAP_X+MAP_W, MAP_Y+MAP_H); glVertex2f(MAP_X, MAP_Y+MAP_H)
    glEnd()
    WORLD_W = 160.0; WORLD_H = MOON_RADIUS + 80.0; WORLD_BOTTOM = MOON_CENTER_Y
    def w2m(wx, wy):
        return MAP_X + (wx+80.0)/WORLD_W*MAP_W, MAP_Y + (wy-WORLD_BOTTOM)/WORLD_H*MAP_H
    glColor3f(0.6, 0.6, 0.62)
    glBegin(GL_LINE_STRIP)
    for a in range(-70, 71, 5):
        rad = math.radians(a)
        mx, my = w2m(MOON_RADIUS*math.sin(rad), MOON_CENTER_Y+MOON_RADIUS*math.cos(rad))
        glVertex2f(mx, my)
    glEnd()
    px, py = w2m(0, MOON_SURFACE_Y+0.5)
    glColor3f(0.95, 0.9, 0.1); glPointSize(5.0)
    glBegin(GL_POINTS); glVertex2f(px, py); glEnd()
    rx, ry = w2m(rocket_x, rocket_y)
    glColor3f(0.2, 1.0, 0.4); glPointSize(6.0)
    glBegin(GL_POINTS); glVertex2f(rx, ry); glEnd()
    glPointSize(1.0)
    draw_bold_text(MAP_X+4, MAP_Y+MAP_H+3, "RADAR", 0.3, 0.5, 0.9)
    glEnable(GL_DEPTH_TEST)


def draw_hud():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    draw_bold_text(330, 775, "LUNAR DESCENT  -  " + rocket_list[selected_rocket_for_game], 0.2, 1.0, 0.5)
    altitude = max(0.0, math.sqrt(rocket_x**2 + (rocket_y-MOON_CENTER_Y)**2) - MOON_RADIUS)
    draw_bold_text(14, 745, "ALTITUDE : {:6.1f} m".format(altitude),       0.7, 0.9, 1.0)
    vy_col = (0.2,1.0,0.2) if abs(rocket_vy) < 0.08 else (1.0,0.45,0.1)
    draw_bold_text(14, 722, "VERT VEL : {:+.3f}".format(rocket_vy),        *vy_col)
    vx_col = (0.2,1.0,0.2) if abs(rocket_vx) < 0.08 else (1.0,0.45,0.1)
    draw_bold_text(14, 699, "HORIZ VEL: {:+.3f}".format(rocket_vx),        *vx_col)
    ang_from_vert = rocket_angle % 360
    ang_disp = ang_from_vert if ang_from_vert <= 180 else ang_from_vert - 360
    ang_col = (0.2,1.0,0.2) if abs(ang_disp) < 20 else (1.0,0.55,0.1)
    draw_bold_text(14, 676, "ANGLE    : {:+.1f} deg".format(ang_disp),     *ang_col)
    draw_bold_text(14, 653, "THRUST   : {}".format("ON" if rocket_thrusting else "OFF"),
                   1.0 if rocket_thrusting else 0.4,
                   0.65 if rocket_thrusting else 0.4,
                   0.1 if rocket_thrusting else 0.4)
    draw_bold_text(14, 625, "-- CONTROLS --",    0.35,0.35,0.55)
    draw_bold_text(14, 605, "UP    : THRUST",    0.45,0.45,0.65)
    draw_bold_text(14, 585, "LEFT  : ROTATE L",  0.45,0.45,0.65)
    draw_bold_text(14, 565, "RIGHT : ROTATE R",  0.45,0.45,0.65)
    draw_bold_text(14, 545, "R     : RESET",     0.45,0.45,0.65)
    draw_bold_text(14, 525, "ESC   : MENU",      0.45,0.45,0.65)
    bar_x, bar_y = 14, 490
    draw_bold_text(bar_x, bar_y+18, "ALIGN (nose up = 0 deg):", 0.55,0.55,0.55)
    glColor3f(0.2, 0.2, 0.25)
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y); glVertex2f(bar_x+180, bar_y)
    glVertex2f(bar_x+180, bar_y+12); glVertex2f(bar_x, bar_y+12)
    glEnd()
    needle = max(-90, min(90, ang_disp))
    needle_x = bar_x + int((needle+90)/180.0*180)
    nd_col = (0.2,1.0,0.2) if abs(needle) < 20 else (1.0,0.45,0.1)
    glColor3f(*nd_col)
    glBegin(GL_QUADS)
    glVertex2f(needle_x-3, bar_y+1); glVertex2f(needle_x+3, bar_y+1)
    glVertex2f(needle_x+3, bar_y+11); glVertex2f(needle_x-3, bar_y+11)
    glEnd()
    glColor3f(0.7, 0.7, 0.2)
    glBegin(GL_LINES)
    glVertex2f(bar_x+90, bar_y); glVertex2f(bar_x+90, bar_y+12)
    glEnd()
    if game_landed:
        msg = "** SUCCESSFUL LANDING! **"
        cx = 500 - len(msg)*4
        draw_bold_text(cx, 420, msg, 0.1, 1.0, 0.3)
        draw_bold_text(cx+20, 393, "Press R to fly again", 0.8, 0.8, 0.8)
    elif game_crashed:
        msg = "** ROCKET CRASHED! **"
        cx = 500 - len(msg)*4
        draw_bold_text(cx, 420, msg, 1.0, 0.15, 0.1)
        if game_message:
            draw_bold_text(cx+10, 393, game_message, 1.0, 0.6, 0.2)
        draw_bold_text(cx+20, 365, "Press R to reset", 0.8, 0.8, 0.8)
    draw_mini_map()
    glEnable(GL_DEPTH_TEST)
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def update_gameplay():
    global rocket_x, rocket_y, rocket_vx, rocket_vy, rocket_angle
    global rocket_thrusting, game_landed, game_crashed, game_message, game_msg_timer
    global cam_look_x, cam_look_y
    if game_landed or game_crashed: return
    if GLUT_KEY_LEFT  in keys_held: rocket_angle -= ROTATION_SPEED
    if GLUT_KEY_RIGHT in keys_held: rocket_angle += ROTATION_SPEED
    rocket_thrusting = (GLUT_KEY_UP in keys_held)
    if rocket_thrusting:
        nose_rad = math.radians(rocket_angle)
        rocket_vx += math.sin(nose_rad) * THRUST_POWER
        rocket_vy += math.cos(nose_rad) * THRUST_POWER
        spawn_flame_particles()
    # Gravity pulls toward moon center
    dx_grav = 0.0 - rocket_x
    dy_grav = MOON_CENTER_Y - rocket_y
    dist_to_center = math.sqrt(dx_grav**2 + dy_grav**2)
    if dist_to_center > 0:
        rocket_vx += (dx_grav / dist_to_center) * abs(GRAVITY)
        rocket_vy += (dy_grav / dist_to_center) * abs(GRAVITY)
    # Linear drag (space friction for controllability)
    rocket_vx *= LINEAR_DRAG
    rocket_vy *= LINEAR_DRAG
    speed = math.sqrt(rocket_vx**2 + rocket_vy**2)
    if speed > MAX_SPEED:
        rocket_vx = rocket_vx / speed * MAX_SPEED
        rocket_vy = rocket_vy / speed * MAX_SPEED
    rocket_x += rocket_vx; rocket_y += rocket_vy
    if rocket_x >  90: rocket_x =  90; rocket_vx = -abs(rocket_vx)*0.3
    if rocket_x < -90: rocket_x = -90; rocket_vx =  abs(rocket_vx)*0.3
    if rocket_y > MOON_SURFACE_Y+130: rocket_y = MOON_SURFACE_Y+130; rocket_vy = 0
    cam_look_x += (rocket_x - cam_look_x) * CAM_SMOOTH
    cam_look_y += (rocket_y - cam_look_y) * CAM_SMOOTH
    dist_from_center = math.sqrt(rocket_x**2 + (rocket_y-MOON_CENTER_Y)**2)
    if dist_from_center - ROCKET_SCALE*0.45 <= MOON_RADIUS + 0.3:
        ratio = (MOON_RADIUS + ROCKET_SCALE*0.45) / dist_from_center if dist_from_center > 0 else 1.0
        rocket_x = rocket_x * ratio
        rocket_y = MOON_CENTER_Y + (rocket_y - MOON_CENTER_Y) * ratio
        rocket_vx = 0; rocket_vy = 0
        land_ang = math.degrees(math.atan2(rocket_x, rocket_y - MOON_CENTER_Y))
        on_pad    = abs(land_ang) <= 6.0
        ang_from_vert = rocket_angle % 360
        ang_disp  = ang_from_vert if ang_from_vert <= 180 else ang_from_vert - 360
        safe_angle = abs(ang_disp) < 22
        on_rock = any(abs(land_ang - rock['angle']) < rock['r']*1.4 for rock in obstacle_rocks)
        if on_rock:
            game_crashed = True; game_message = "Smashed into a boulder!"
        elif not on_pad:
            game_crashed = True; game_message = "Missed the landing pad!"
        elif not safe_angle:
            game_crashed = True; game_message = "Too tilted on touchdown!"
        else:
            game_landed = True; game_message = "Flawless landing!"
    update_flame_particles()

# ============================================================
# ROCKET SELECTION SCREEN
# ============================================================
def draw_rocket_selection_screen():
    glClearColor(0.04, 0.04, 0.10, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(45, 1.25, 0.1, 500.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    glPointSize(2.0)
    glBegin(GL_POINTS)
    random.seed(STAR_SEED)
    for i in range(400):
        blink = 0.4 + 0.6 * abs(math.sin(animation_time * 3 + i * 0.7))
        bright = random.uniform(0.5, 1.0)
        glColor3f(blink*bright, blink*bright, blink*bright)
        glVertex3f(random.uniform(-18, 18), random.uniform(-4, 10), -30)
    random.seed()
    glEnd()
    glEnable(GL_DEPTH_TEST)
    rocket_positions  = [(-7.0,-1.5,-18.0),(0.0,-1.5,-18.0),(7.0,-1.5,-18.0)]
    rocket_draw_funcs = [draw_jak_hound, draw_eva_nation, draw_jf17_thunder]
    for i, (rx, ry, rz) in enumerate(rocket_positions):
        glPushMatrix(); glTranslatef(rx, ry, rz)
        if i == selected_rocket_index:
            glRotatef(animation_time*60, 0,1,0)
            glTranslatef(0, 0.3*math.sin(animation_time*2), 0)
            glScalef(1.25,1.25,1.25)
        else:
            glRotatef(animation_time*25, 0,1,0)
            glScalef(0.9,0.9,0.9)
        rocket_draw_funcs[i]()
        glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    draw_bold_text(335, 760, "CHOOSE YOUR SPACECRAFT", 1.0, 0.85, 0.1)
    label_xs = [165, 500, 825]
    for i, lx in enumerate(label_xs):
        col = (0.1,1.0,0.3) if i == selected_rocket_index else (0.65,0.65,0.65)
        name = rocket_list[i]
        draw_bold_text(lx - len(name)*4, 205, name, *col)
        if i == selected_rocket_index:
            draw_bold_text(lx-30, 185, "< SELECTED >", 0.1, 0.9, 0.3)
    draw_bold_text(330, 158, "LEFT / RIGHT ARROW: Change Rocket",  0.55,0.55,0.55)
    draw_bold_text(340, 133, "ENTER or SPACE: Confirm & Launch",   0.55,0.55,0.55)
    draw_bold_text(395, 108, "ESC: Back to Menu",                  0.55,0.55,0.55)
    draw_button(500, 65, "LAUNCH  " + rocket_list[selected_rocket_index], 10)
    glEnable(GL_DEPTH_TEST)
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# ============================================================
# MAIN DISPLAY
# ============================================================
def display():
    glClearColor(0.04, 0.04, 0.10, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    if current_state in ["MENU", "OPTIONS"]:
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(45, 1.25, 0.1, 500.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        draw_interactive_scene()
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        gluOrtho2D(0, 1000, 0, 800)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        active_list = main_menu if current_state == "MENU" else options_menu
        for i, option in enumerate(active_list):
            draw_button(500, 500 - (i * 90), option, i)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state == "ROCKET_SELECT":
        draw_rocket_selection_screen()

    elif current_state == "ROCKET_LIST":
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        gluOrtho2D(0, 1000, 0, 800)
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
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(45, 1.25, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        glTranslatef(0, 0, -25 * zoom_level)
        glRotatef(cam_x, 1, 0, 0); glRotatef(cam_y, 0, 1, 0)
        if   selected_rocket_index == 0: draw_jak_hound()
        elif selected_rocket_index == 1: draw_eva_nation()
        elif selected_rocket_index == 2: draw_jf17_thunder()
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        gluOrtho2D(0, 1000, 0, 800)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        draw_bold_text(20, 750, "INSPECTING: " + rocket_list[selected_rocket_index], 1, 1, 0)
        if selected_rocket_for_game == selected_rocket_index:
            draw_bold_text(20, 720, "SELECTED FOR MISSION! | F: RESELECT", 0, 1, 0)
        else:
            draw_bold_text(20, 720, "PRESS F TO SELECT THIS ROCKET", 0.7, 0.7, 0.7)
        draw_bold_text(20, 690, "ARROWS: ROTATE | N: ZOOM IN | M: ZOOM OUT | ESC: BACK", 0.5, 0.5, 0.5)
        draw_button(150, 50, " BACK ", 99)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state == "GAMEPLAY":
        glClearColor(0.01, 0.01, 0.05, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(62, 1.25, 0.5, 900.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        dist_from_moon = math.sqrt(cam_look_x**2 + (cam_look_y - MOON_CENTER_Y)**2)
        eye_dist = max(90.0, dist_from_moon * 1.8 + 45.0)
        eye_x  = cam_look_x * 0.25
        eye_y  = cam_look_y * 0.25 + 8.0
        eye_z  = eye_dist
        look_x = cam_look_x * 0.15
        look_y = cam_look_y * 0.15 - 5.0
        look_z = -12.0
        gluLookAt(eye_x, eye_y, eye_z, look_x, look_y, look_z, 0, 1, 0)
        draw_deep_stars()
        draw_space_background()
        draw_earth()
        draw_moon_body()
        draw_moon_surface_details()
        draw_flame_particles()
        draw_gameplay_rocket()
        draw_hud()

    glutSwapBuffers()

# ============================================================
# INPUT
# ============================================================
def special_keys(key, x, y):
    global cam_x, cam_y, selected_option, current_state, selected_rocket_index, keys_held
    if current_state == "GAMEPLAY":
        keys_held.add(key); return
    if current_state == "ROCKET_SELECT":
        if key == GLUT_KEY_LEFT:  selected_rocket_index = (selected_rocket_index - 1) % 3
        elif key == GLUT_KEY_RIGHT: selected_rocket_index = (selected_rocket_index + 1) % 3
        glutPostRedisplay(); return
    if current_state == "ROCKET_VIEWER":
        if key == GLUT_KEY_LEFT:    cam_y -= 5.0
        elif key == GLUT_KEY_RIGHT: cam_y += 5.0
        elif key == GLUT_KEY_UP:    cam_x -= 5.0
        elif key == GLUT_KEY_DOWN:  cam_x += 5.0
    elif current_state in ["MENU", "OPTIONS", "ROCKET_LIST"]:
        menu_items = (main_menu if current_state == "MENU"
                      else options_menu if current_state == "OPTIONS" else rocket_list)
        max_options = len(menu_items) - 1
        if selected_option < 0 or selected_option > max_options: selected_option = 0
        if key == GLUT_KEY_UP:
            selected_option = max(0, (selected_option-1) % (max_options+1))
        elif key == GLUT_KEY_DOWN:
            selected_option = min(max_options, (selected_option+1) % (max_options+1))
    glutPostRedisplay()

def special_keys_up(key, x, y):
    global keys_held
    keys_held.discard(key)
    glutPostRedisplay()

def mouse_click(button, state, x, y):
    global current_state, selected_option, selected_rocket_index, last_click_x, last_click_y
    global selected_rocket_for_game, rocket_selected, show_alert, alert_message
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        last_click_x, last_click_y = x, y
        ly = 800 - y
        if current_state == "ROCKET_SELECT":
            zones = [(0,333),(333,666),(666,1000)]
            for i, (zx1, zx2) in enumerate(zones):
                if zx1 <= x <= zx2 and 220 <= ly <= 700:
                    selected_rocket_index = i; return
            if 250 <= x <= 750 and 50 <= ly <= 85:
                selected_rocket_for_game = selected_rocket_index
                rocket_selected = True; reset_gameplay(); current_state = "GAMEPLAY"
        elif current_state == "ROCKET_LIST":
            for i in range(3):
                if 400 <= x <= 600 and (500-(i*100)-10) <= ly <= (500-(i*100)+25):
                    selected_rocket_index, current_state = i, "ROCKET_VIEWER"
            if 400 <= x <= 600 and 190 <= ly <= 215:
                if not rocket_selected: show_alert = True; alert_message = "Select your Spacecraft first!!"
                else: current_state = "GAMEPLAY"
            if x <= 250 and ly <= 100: current_state = "OPTIONS"; selected_option = 1
        elif current_state == "ROCKET_VIEWER":
            if x <= 250 and ly <= 100: current_state = "ROCKET_LIST"
        else:
            active_list = main_menu if current_state == "MENU" else options_menu
            for i, opt in enumerate(active_list):
                if 400 <= x <= 600 and (500-(i*90)-10) <= ly <= (500-(i*90)+25):
                    if selected_option == i:
                        if current_state == "MENU":
                            if i == 0: current_state = "ROCKET_SELECT"; selected_option = -1
                            elif i == 1: current_state = "OPTIONS"; selected_option = -1
                            elif i == 2: os._exit(0)
                        elif current_state == "OPTIONS":
                            if i == 1: current_state = "ROCKET_LIST"; selected_option = -1
                            elif i == 2: current_state = "MENU"; selected_option = 1
                    else: selected_option = i
    glutPostRedisplay()

def keyboard(key, x, y):
    global current_state, selected_option, zoom_level, selected_rocket_index
    global selected_rocket_for_game, rocket_selected, show_alert, alert_message
    if ord(key) == 27:
        if current_state == "GAMEPLAY":        current_state = "MENU"; selected_option = -1
        elif current_state == "OPTIONS":       current_state = "MENU"; selected_option = 1
        elif current_state == "ROCKET_SELECT": current_state = "MENU"; selected_option = -1
        elif current_state == "ROCKET_LIST":   current_state = "OPTIONS"; selected_option = 1; show_alert = False
        elif current_state == "ROCKET_VIEWER": current_state = "ROCKET_LIST"; selected_option = selected_rocket_index
    if key in (b'r', b'R') and current_state == "GAMEPLAY":
        reset_gameplay()
    if current_state in ["MENU", "OPTIONS", "ROCKET_LIST"]:
        menu_items = (main_menu if current_state == "MENU"
                      else options_menu if current_state == "OPTIONS" else rocket_list)
        max_options = len(menu_items) - 1
        if selected_option < 0 or selected_option > max_options: selected_option = 0
        if key == b'\r' or key == b' ':
            if current_state == "MENU":
                if selected_option == 0: current_state = "ROCKET_SELECT"; selected_option = -1
                elif selected_option == 1: current_state = "OPTIONS"; selected_option = -1
                elif selected_option == 2: os._exit(0)
            elif current_state == "OPTIONS":
                if selected_option == 1: current_state = "ROCKET_LIST"; selected_option = -1
                elif selected_option == 2: current_state = "MENU"; selected_option = 1
            elif current_state == "ROCKET_LIST":
                if 0 <= selected_option < 3: selected_rocket_index = selected_option; current_state = "ROCKET_VIEWER"
                elif selected_option == 3:
                    if not rocket_selected: show_alert = True; alert_message = "Select your Spacecraft first!!"
                    else: current_state = "GAMEPLAY"
    if current_state == "ROCKET_SELECT":
        if key == b'\r' or key == b' ':
            selected_rocket_for_game = selected_rocket_index
            rocket_selected = True; reset_gameplay(); current_state = "GAMEPLAY"
    if current_state == "ROCKET_VIEWER":
        if   key in (b'n', b'N'): zoom_level = max(0.2, zoom_level - 0.1)
        elif key in (b'm', b'M'): zoom_level = min(3.0, zoom_level + 0.1)
        elif key in (b'f', b'F'): selected_rocket_for_game = selected_rocket_index; rocket_selected = True
    glutPostRedisplay()

def idle():
    global animation_time, planet_rotation_y
    animation_time += 0.016
    planet_rotation_y += 0.015
    if current_state == "GAMEPLAY":
        update_gameplay()
    glutPostRedisplay()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutCreateWindow(b"Lunar Descent")
    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutMouseFunc(mouse_click)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutSpecialUpFunc(special_keys_up)
    glutMainLoop()

if __name__ == "__main__":
    main()