from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math, random, os as _os

WIN_W, WIN_H = 1000, 800

# ═══════════════════════════════════════════════════════════════════════════
#  GLOBAL STATE
# ═══════════════════════════════════════════════════════════════════════════
current_state            = "MENU"
selected_option          = 0
selected_rocket_index    = 0
selected_rocket_for_game = -1
rocket_selected          = False
show_alert               = False
alert_message            = ""
last_click_x, last_click_y = -1000, -1000
animation_time           = 0.0
planet_rotation_y        = 0.0

cam_rx, cam_ry = 15.0, 0.0
zoom_level     = 1.0

main_menu    = ["START GAME", "CHECK ROCKET", "QUIT"]
rocket_list  = ["JakHound F-22", "EvaNation F-15", "JF17 Thunder", "START MISSION"]

# ── Lander ──────────────────────────────────────────────────────────────────
lander_x = 0.0; lander_y = 80.0; lander_z = 0.0
vel_x = vel_y = vel_z = 0.0
fuel = 100.0; oxygen = 100.0
game_started = False; game_over = False; landing_msg = ""
lander_tilt_z = lander_tilt_x = rocket_heading = 0.0
gp_cam_pitch = 22.0; gp_cam_dist = 45.0

score = 0; level = 1
target_x = target_z = 0.0; target_surface_y = 0.0
new_target_flash_start = -999.0
MAX_TILT = 22.0; TILT_SPEED = 1.6; TILT_RECOVERY = 2.8; FUEL_REGEN = 0.28

# ── Key state (press/release) ────────────────────────────────────────────────
key_state = {}

def key_held(t):        return key_state.get(t, False)
def key_up_held():      return key_held(b'\x00up')
def key_dn_held():      return key_held(b'\x00dn')
def key_w_held():       return key_held(b'w')
def key_s_held():       return key_held(b's')
def key_a_held():       return key_held(b'a')
def key_d_held():       return key_held(b'd')
def key_left_held():    return key_held(b'\x00lt')
def key_right_held():   return key_held(b'\x00rt')

def _set_key(t, v):
    global game_started
    key_state[t] = v
    if v and current_state == "GAMEPLAY":
        game_started = True

def _clear_keys():
    for t in list(key_state): key_state[t] = False

# ═══════════════════════════════════════════════════════════════════════════
#  DIFFICULTY
# ═══════════════════════════════════════════════════════════════════════════
def diff_gravity():      return max(-0.016, -0.007  - (level-1)*0.00075)
def diff_drag():         return max(0.945,   0.980  - (level-1)*0.0038)
def diff_thrust_up():    return 0.020
def diff_thrust_horiz(): return 0.007
def diff_max_vel():      return 0.45
def diff_fuel_burn():    return max(0.09, 0.12 + (level-1)*0.004)
def get_land_vel_max():  return max(4.5,  22.0 - (level-1)*1.8)
def get_target_radius(): return max(0.8,   6.5 - (level-1)*0.60)
def get_wind():
    if level < 4: return 0.0, 0.0
    s = (level-3)*0.00028; a = math.radians(animation_time*4.0)
    return math.cos(a)*s, math.sin(a)*s

# ═══════════════════════════════════════════════════════════════════════════
#  TERRAIN  (procedural, stored as vertex grid, drawn with GL_TRIANGLES)
# ═══════════════════════════════════════════════════════════════════════════
WORLD_HALF   = 320
TERRAIN_DIVS = 60          # reduced for performance without display lists
_mountains   = []
_craters     = []
_terrain_verts = []        # precomputed flat list for drawing

def terrain_height(wx, wz):
    y = 0.0
    for (cx, cz, rad, pk) in _mountains:
        d = math.sqrt((wx-cx)**2+(wz-cz)**2)
        if d < rad:
            t = 1.0 - d/rad; y += pk*t*t*(3.0-2.0*t)
    for (cx, cz, rad, dep) in _craters:
        d = math.sqrt((wx-cx)**2+(wz-cz)**2)
        if d < rad:
            t = d/rad
            y += -dep*(1.0-t*t) + dep*0.42*math.exp(-((t-0.86)/0.07)**2)
    return y

def generate_terrain():
    global _mountains, _craters, _terrain_verts
    rng = random.Random(level*31+7)
    _mountains = []
    for _ in range(16+level*2):
        _mountains.append((rng.uniform(-WORLD_HALF+20, WORLD_HALF-20),
                           rng.uniform(-WORLD_HALF+20, WORLD_HALF-20),
                           rng.uniform(28,85), rng.uniform(18,55)))
    for _ in range(4+level):
        _mountains.append((rng.uniform(-WORLD_HALF+40, WORLD_HALF-40),
                           rng.uniform(-WORLD_HALF+40, WORLD_HALF-40),
                           rng.uniform(20,45), rng.uniform(55,90)))
    _craters = []
    for _ in range(20+level*2):
        _craters.append((rng.uniform(-WORLD_HALF+10, WORLD_HALF-10),
                         rng.uniform(-WORLD_HALF+10, WORLD_HALF-10),
                         rng.uniform(8,42), rng.uniform(5,20)))
    # Precompute vertex grid
    step = (WORLD_HALF*2)/TERRAIN_DIVS; cols = TERRAIN_DIVS+1
    verts = []
    for row in range(cols):
        for col in range(cols):
            wx = -WORLD_HALF + col*step; wz = -WORLD_HALF + row*step
            verts.append((wx, terrain_height(wx, wz), wz))
    _terrain_verts = (verts, step, cols)

def draw_terrain():
    if not _terrain_verts: return
    verts, step, cols = _terrain_verts
    glBegin(GL_TRIANGLES)
    for row in range(TERRAIN_DIVS):
        for col in range(TERRAIN_DIVS):
            i00 = row*cols+col; i10 = i00+1; i01 = i00+cols; i11 = i01+1
            for ia, ib, ic in [(i00,i10,i01),(i10,i11,i01)]:
                for idx in (ia, ib, ic):
                    v = verts[idx]
                    t = max(0.0, min(1.0, (v[1]+18)/62.0)); b = 0.18+t*0.36
                    glColor3f(b*0.96, b, b*1.06)
                    glVertex3f(v[0], v[1], v[2])
    glEnd()

def move_target():
    global target_x, target_z, target_surface_y, new_target_flash_start
    rng = random.Random(level*17+score*3+int(animation_time*100))
    spread = min(WORLD_HALF-30, 80+level*9)
    for _ in range(800):
        a = rng.uniform(0,2*math.pi); d = rng.uniform(max(80,spread*0.55),spread)
        tx = math.cos(a)*d; tz = math.sin(a)*d
        if abs(tx)<WORLD_HALF-15 and abs(tz)<WORLD_HALF-15:
            target_x,target_z = tx,tz; break
    target_surface_y = terrain_height(target_x,target_z)
    new_target_flash_start = animation_time
    generate_terrain()

# ═══════════════════════════════════════════════════════════════════════════
#  CAMERA
# ═══════════════════════════════════════════════════════════════════════════
def setup_3d_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(58, WIN_W/WIN_H, 1.0, 1800.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def setup_gameplay_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(58, WIN_W/WIN_H, 1.0, 1800.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    hr = math.radians(rocket_heading); pr = math.radians(gp_cam_pitch)
    ecx = lander_x - math.sin(hr)*gp_cam_dist*math.cos(pr)
    ecy = lander_y + gp_cam_dist*math.sin(pr)
    ecz = lander_z - math.cos(hr)*gp_cam_dist*math.cos(pr)
    gluLookAt(ecx, ecy, ecz, lander_x, lander_y, lander_z, 0, 1, 0)

def setup_menu_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, WIN_W/WIN_H, 0.1, 600.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(0, 0, 60, 0, 0, 0, 0, 1, 0)

def setup_rocket_viewer_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, WIN_W/WIN_H, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    # Orbit camera controlled by cam_rx/cam_ry
    ex = 25*zoom_level * math.sin(math.radians(cam_ry)) * math.cos(math.radians(cam_rx))
    ey = 25*zoom_level * math.sin(math.radians(cam_rx))
    ez = 25*zoom_level * math.cos(math.radians(cam_ry)) * math.cos(math.radians(cam_rx))
    gluLookAt(ex, ey, ez, 0, 1.5, 0, 0, 1, 0)

# ═══════════════════════════════════════════════════════════════════════════
#  HUD TEXT  (glRasterPos2f + glutBitmapCharacter)
# ═══════════════════════════════════════════════════════════════════════════
def draw_text(x, y, text, r=1.0, g=1.0, b=1.0):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glScalef(2.0/WIN_W, 2.0/WIN_H, 1.0)
    glTranslatef(-WIN_W/2.0, -WIN_H/2.0, 0.0)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(r, g, b)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(ch))
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

# ═══════════════════════════════════════════════════════════════════════════
#  GL PRIMITIVES  (only allowed functions)
# ═══════════════════════════════════════════════════════════════════════════
def draw_cylinder(r, h, sides=14):
    step = 2*math.pi/sides
    # Side
    glBegin(GL_QUAD_STRIP)
    for i in range(sides+1):
        a = i*step; ca = math.cos(a); sa = math.sin(a)
        glVertex3f(r*ca, 0, r*sa); glVertex3f(r*ca, h, r*sa)
    glEnd()
    # Caps
    for yy, ny in [(0, -1), (h, 1)]:
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(0, yy, 0)
        rr = range(sides, -1, -1) if ny < 0 else range(sides+1)
        for i in rr: a = i*step; glVertex3f(r*math.cos(a), yy, r*math.sin(a))
        glEnd()

def draw_cone(r, h, sides=14):
    step = 2*math.pi/sides
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0, h, 0)
    for i in range(sides+1): a = i*step; glVertex3f(r*math.cos(a), 0, r*math.sin(a))
    glEnd()
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0, 0, 0)
    for i in range(sides, -1, -1): a = i*step; glVertex3f(r*math.cos(a), 0, r*math.sin(a))
    glEnd()

def draw_box(sx, sy, sz):
    hx, hy, hz = sx/2, sy/2, sz/2
    glBegin(GL_QUADS)
    for vts in [
        [( hx, hy, hz),( hx,-hy, hz),( hx,-hy,-hz),( hx, hy,-hz)],
        [(-hx, hy,-hz),(-hx,-hy,-hz),(-hx,-hy, hz),(-hx, hy, hz)],
        [(-hx, hy,-hz),( hx, hy,-hz),( hx, hy, hz),(-hx, hy, hz)],
        [(-hx,-hy, hz),( hx,-hy, hz),( hx,-hy,-hz),(-hx,-hy,-hz)],
        [(-hx, hy, hz),( hx, hy, hz),( hx,-hy, hz),(-hx,-hy, hz)],
        [( hx, hy,-hz),(-hx, hy,-hz),(-hx,-hy,-hz),( hx,-hy,-hz)]]:
        for v in vts: glVertex3f(*v)
    glEnd()

def draw_sphere_gl(r, stacks=10, slices=14):
    q = gluNewQuadric()
    gluSphere(q, r, slices, stacks)

def draw_disk(r, sides=14):
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0, 0, 0)
    for i in range(sides+1): a = 2*math.pi*i/sides; glVertex3f(r*math.cos(a), 0, r*math.sin(a))
    glEnd()

# ═══════════════════════════════════════════════════════════════════════════
#  ROCKET MODELS
# ═══════════════════════════════════════════════════════════════════════════
def draw_jak_hound():
    glColor3f(0.14,0.14,0.16); draw_cylinder(0.30,2.10,8)
    glColor3f(0.85,0.60,0.10)
    glPushMatrix(); glTranslatef(0,1.65,0); draw_cylinder(0.31,0.22,8); glPopMatrix()
    glColor3f(0.05,0.55,0.95)
    glPushMatrix(); glTranslatef(0,1.52,0.33); draw_sphere_gl(0.09,6,8); glPopMatrix()
    glColor3f(0.75,0.55,0.08)
    for py in [0.30,0.65,1.00,1.35]:
        glPushMatrix(); glTranslatef(0,py,0.29); draw_box(0.34,0.025,0.04); glPopMatrix()
    glColor3f(0.18,0.18,0.20)
    glPushMatrix(); glTranslatef(0,2.10,0); draw_cone(0.28,0.95,8); glPopMatrix()
    glColor3f(0.80,0.60,0.10)
    glPushMatrix(); glTranslatef(0,3.05,0); draw_sphere_gl(0.07,6,8); glPopMatrix()
    glColor3f(0.12,0.12,0.14); draw_disk(0.32,8)
    for i in range(4):
        glColor3f(0.12,0.12,0.14); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.30,0.10,0); draw_box(0.40,0.65,0.05); glPopMatrix()
        glColor3f(0.75,0.55,0.08); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.50,0.10,0); draw_box(0.04,0.65,0.055); glPopMatrix()
    glColor3f(0.20,0.20,0.22)
    glPushMatrix(); glTranslatef(0,-0.28,0); draw_cylinder(0.20,0.28,8); glPopMatrix()
    glColor3f(0.75,0.55,0.08); draw_disk(0.22,8)

def draw_eva_nation():
    glColor3f(0.95,0.55,0.75); draw_cylinder(0.40,2.2,16)
    glColor3f(0.97,0.97,0.97)
    glPushMatrix(); glTranslatef(0,0.8,0.42); draw_box(0.28,0.70,0.05); glPopMatrix()
    glColor3f(0.85,0.72,0.30)
    for yw in [0.5,0.9,1.30]:
        glPushMatrix(); glTranslatef(0,yw,0.42); draw_box(0.30,0.04,0.06); glPopMatrix()
    glColor3f(0.90,0.40,0.65)
    glPushMatrix(); glTranslatef(0,2.2,0); draw_cone(0.38,1.10,16); glPopMatrix()
    glColor3f(1.0,0.80,0.90)
    glPushMatrix(); glTranslatef(0,3.30,0); draw_sphere_gl(0.08,6,8); glPopMatrix()
    glColor3f(0.85,0.45,0.70); draw_disk(0.42,16)
    for i,col in enumerate([(0.80,0.35,0.60),(0.90,0.45,0.70),(0.80,0.35,0.60),(0.90,0.45,0.70)]):
        glColor3f(*col); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.38,0.10,0); draw_box(0.55,0.85,0.06); glPopMatrix()

def draw_jf17_thunder():
    glColor3f(0.55,0.05,0.05); draw_cylinder(0.32,2.0,6)
    glColor3f(0.70,0.08,0.08)
    for py,sz in [(1.50,0.30),(0.90,0.28),(0.35,0.28)]:
        glPushMatrix(); glTranslatef(0,py,0.33); draw_box(0.24,sz,0.05); glPopMatrix()
    glColor3f(1.0,0.20,0.05)
    for yy in [0.20,0.60,1.00,1.40,1.80]:
        glPushMatrix(); glTranslatef(0,yy,0.31); draw_box(0.30,0.03,0.04); glPopMatrix()
    glColor3f(0.65,0.07,0.07)
    glPushMatrix(); glTranslatef(0,2.0,0); draw_cone(0.30,0.90,6); glPopMatrix()
    glColor3f(0.9,0.3,0.3)
    glPushMatrix(); glTranslatef(0,2.90,0); draw_sphere_gl(0.06,6,8); glPopMatrix()
    glColor3f(0.45,0.04,0.04); draw_disk(0.34,6)
    for i in range(4):
        glColor3f(0.50,0.05,0.05); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.44,0.15,0); draw_box(0.40,0.70,0.06); glPopMatrix()
    flame = 0.5+0.5*math.sin(animation_time*8.0)
    glColor3f(1.0,0.4+0.3*flame,0.0)
    glPushMatrix(); glTranslatef(0,-0.05,0); draw_cone(0.15,0.5+0.4*flame,12); glPopMatrix()

def draw_selected_rocket():
    if   selected_rocket_for_game==0: draw_jak_hound()
    elif selected_rocket_for_game==1: draw_eva_nation()
    elif selected_rocket_for_game==2: draw_jf17_thunder()
    else: draw_jak_hound()

# ═══════════════════════════════════════════════════════════════════════════
#  SPACE BACKGROUND  (stars + planets)
# ═══════════════════════════════════════════════════════════════════════════
_star_seed = 7
def draw_space_background():
    glBegin(GL_POINTS)
    random.seed(_star_seed)
    for _ in range(500):
        ang = random.uniform(0,2*math.pi); el = random.uniform(-math.pi/2,math.pi/2)
        b = random.uniform(0.6,1.0)
        glColor3f(b, b, min(1.0,b+0.1))
        glVertex3f(450*math.cos(el)*math.cos(ang), 450*math.sin(el), 450*math.cos(el)*math.sin(ang))
    glEnd()
    glPushMatrix(); glRotatef(planet_rotation_y*0.1,0,1,0); glTranslatef(400,100,0)
    glColor3f(1.0,0.9,0.3); draw_sphere_gl(22,12,18); glPopMatrix()
    glPushMatrix(); glRotatef(planet_rotation_y*0.3,0,1,0); glTranslatef(260,40,-130)
    glColor3f(0.1,0.4,0.8); draw_sphere_gl(12,10,16)
    glColor3f(0.9,0.9,0.9)
    glPushMatrix(); glRotatef(planet_rotation_y*2,0,1,0); draw_sphere_gl(12.3,5,8); glPopMatrix()
    glPopMatrix()
    glPushMatrix(); glRotatef(planet_rotation_y*0.2,0,1,0); glTranslatef(-220,-25,180)
    glColor3f(0.7,0.25,0.1); draw_sphere_gl(7,8,12); glPopMatrix()

# ═══════════════════════════════════════════════════════════════════════════
#  MENU BACKGROUND  (stars + rotating planet, drawn in 3D)
# ═══════════════════════════════════════════════════════════════════════════
star_data = []
for _ in range(300):
    _tx,_ty = random.uniform(-80,80), random.uniform(-50,50)
    star_data.append([_tx,_ty,random.uniform(-120,-20),random.uniform(0.5,0.9)])

def draw_menu_scene():
    glBegin(GL_POINTS)
    for i,s in enumerate(star_data):
        blink = 0.3+0.5*abs(math.sin(animation_time*4+i))
        glColor3f(blink*s[3], blink*s[3], blink*s[3])
        glVertex3f(s[0], s[1], s[2])
    glEnd()
    glPushMatrix(); glTranslatef(18,-10,10)
    glRotatef(planet_rotation_y, 0,1,0)
    glColor3f(0.75,0.75,0.80); draw_sphere_gl(7,14,20)
    glColor3f(0.28,0.28,0.30)
    glPushMatrix(); glRotatef(animation_time*6,1,1,0); draw_sphere_gl(7.1,5,7); glPopMatrix()
    glPopMatrix()

# ═══════════════════════════════════════════════════════════════════════════
#  MENU BUTTONS  (drawn with GL_QUADS + text)
# ═══════════════════════════════════════════════════════════════════════════
def draw_menu_button(label, index, cx, cy):
    """Draw a 2D button using screen-space coordinates via text system."""
    sel = (selected_option == index)
    r,g,b = (1.0,1.0,1.0) if sel else (0.7,0.15,0.15)
    draw_text(cx - len(label)*4, cy, label, r, g, b)
    # Underline for selected
    if sel:
        draw_text(cx - len(label)*4 - 3, cy, "> " + label + " <", 1.0, 0.3, 0.3)

def draw_menu_buttons():
    items = main_menu if current_state == "MENU" else rocket_list
    draw_text(WIN_W//2 - 80, WIN_H - 60, "LUNAR DESCENT", 0.8, 0.8, 1.0)
    for i, label in enumerate(items):
        cy = 500 - i*80
        sel = (selected_option == i)
        col = (1.0,0.9,0.2) if sel else (0.6,0.1,0.1)
        prefix = ">>  " if sel else "    "
        draw_text(WIN_W//2 - len(label)*5 - 30, cy, prefix + label, *col)
    if show_alert:
        draw_text(WIN_W//2 - 120, 300, alert_message, 1.0, 0.2, 0.2)

# ═══════════════════════════════════════════════════════════════════════════
#  TARGET MARKER
# ═══════════════════════════════════════════════════════════════════════════
def draw_target():
    cx,cz = target_x,target_z; sy = terrain_height(cx,cz)
    rad = get_target_radius(); pulse = 0.5+0.5*math.sin(animation_time*4.0)
    danger = min(1.0,(level-1)/9.0); tg = 1.0-danger*0.8
    # Rings
    for ring_r,thick in [(rad+2.0,3.5),(rad,2.5),(rad*0.5,2.0)]:
        glColor3f(1.0, tg*(pulse*0.8+0.2), 0.0)
        glBegin(GL_LINE_LOOP)
        for s in range(48):
            a = 2*math.pi*s/48; wx2 = cx+ring_r*math.cos(a); wz2 = cz+ring_r*math.sin(a)
            glVertex3f(wx2, terrain_height(wx2,wz2)+0.15, wz2)
        glEnd()
    # Crosshair
    glColor3f(1.0,tg,0.0)
    glBegin(GL_LINES)
    glVertex3f(cx-(rad+3),sy+0.15,cz); glVertex3f(cx+(rad+3),sy+0.15,cz)
    glVertex3f(cx,sy+0.15,cz-(rad+3)); glVertex3f(cx,sy+0.15,cz+(rad+3))
    glEnd()
    # Beacon line
    bh = sy+38.0+pulse*5.0
    glColor3f(1.0,tg,0.0)
    glBegin(GL_LINES); glVertex3f(cx,sy+0.1,cz); glVertex3f(cx,bh,cz); glEnd()
    # Beacon dot
    glPushMatrix(); glTranslatef(cx,bh,cz)
    glColor3f(1.0,1.0,0.2*pulse); draw_sphere_gl(0.8,5,8)
    glPopMatrix()

def draw_heading_indicator():
    sy = terrain_height(lander_x,lander_z)
    hr = math.radians(rocket_heading)
    ex2 = lander_x+math.sin(hr)*6; ez2 = lander_z+math.cos(hr)*6
    glColor3f(0.0,1.0,1.0)
    glBegin(GL_LINES)
    glVertex3f(lander_x,sy+0.4,lander_z); glVertex3f(ex2,terrain_height(ex2,ez2)+0.4,ez2)
    glEnd()

# ═══════════════════════════════════════════════════════════════════════════
#  THRUST FLAMES
# ═══════════════════════════════════════════════════════════════════════════
def draw_thrust_flame():
    if not key_up_held() or (fuel<=0 and oxygen<=0): return
    on_oxy = (fuel<=0 and oxygen>0); flame = 0.5+0.5*math.sin(animation_time*15.0)
    if on_oxy: glColor3f(0.4,0.6+0.3*flame,1.0)
    else:      glColor3f(1.0,0.5+0.3*flame,0.0)
    glPushMatrix(); glTranslatef(0,-0.5,0); draw_cone(0.3,1.0+0.6*flame,12); glPopMatrix()

def draw_retro_flame():
    if not key_dn_held() or (fuel<=0 and oxygen<=0): return
    flame = 0.4+0.4*math.sin(animation_time*15.0); glColor3f(0.5,0.8+0.2*flame,1.0)
    glPushMatrix(); glTranslatef(0,2.5,0); glRotatef(180,1,0,0); draw_cone(0.2,0.6+0.4*flame,12); glPopMatrix()

# ═══════════════════════════════════════════════════════════════════════════
#  TRAJECTORY PREVIEW
# ═══════════════════════════════════════════════════════════════════════════
def draw_trajectory():
    px,py,pz = lander_x,lander_y,lander_z
    vx,vy,vz = vel_x,vel_y,vel_z; sf,so = fuel,oxygen
    hr = math.radians(rocket_heading)
    fwx = math.sin(hr); fwz = math.cos(hr)
    rtx = math.cos(hr); rtz = -math.sin(hr)
    G=diff_gravity(); DR=diff_drag(); TU=diff_thrust_up()
    TH=diff_thrust_horiz(); FB=diff_fuel_burn(); MX=diff_max_vel()
    pts = [(px,py,pz)]
    for _ in range(400):
        vy+=G; hf=sf>0; ho=so>0
        if key_up_held():
            if hf: vy+=TU; sf=max(0,sf-FB)
            elif ho: vy+=TU*0.55; so=max(0,so-0.10)
        if key_w_held(): vx+=fwx*TH; vz+=fwz*TH
        if key_s_held(): vx-=fwx*TH; vz-=fwz*TH
        if key_a_held(): vx-=rtx*TH; vz-=rtz*TH
        if key_d_held(): vx+=rtx*TH; vz+=rtz*TH
        vx*=DR; vz*=DR
        vx=max(-MX,min(MX,vx)); vz=max(-MX,min(MX,vz)); vy=max(-MX,min(MX,vy))
        px+=vx; py+=vy; pz+=vz
        gy = terrain_height(px,pz)
        if py<=gy+0.5: pts.append((px,py,pz)); break
        pts.append((px,py,pz))
    if len(pts) < 2: return
    spd = math.sqrt(vx**2+vy**2+vz**2)*60; lv = get_land_vel_max()
    lr,lg,lb = (0.2,1.0,0.3) if spd<=lv else (1.0,0.85,0.0) if spd<=lv*1.5 else (1.0,0.2,0.1)
    glBegin(GL_LINE_STRIP)
    for idx,(tx2,ty2,tz2) in enumerate(pts):
        fade = 1.0-(idx/len(pts))*0.7
        glColor3f(lr*fade,lg*fade,lb*fade); glVertex3f(tx2,ty2,tz2)
    glEnd()

# ═══════════════════════════════════════════════════════════════════════════
#  MINIMAP  (drawn in a corner using 2D projection trick — no glViewport)
# ═══════════════════════════════════════════════════════════════════════════
def draw_minimap():
    # Switch to a 2D-like projection centered at top-right corner
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    # Map [0,WIN_W] x [0,WIN_H] to NDC, then offset to top-right quadrant
    # We use gluPerspective + gluLookAt to fake a top-down orthographic view
    # by placing camera very high and using a tight FOV
    gluPerspective(2.0, 1.0, 1.0, 5000.0)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    # Top-down view centered at world origin
    gluLookAt(0, 4000, 0,   0, 0, 0,   0, 0, -1)

    # Scale world to fit minimap area
    half = float(WORLD_HALF+10)
    glScalef(1.0, 1.0, 1.0)

    # Background quad
    glColor3f(0.04,0.04,0.12)
    glBegin(GL_QUADS)
    glVertex3f(-half,0,-half); glVertex3f(half,0,-half)
    glVertex3f(half,0,half);   glVertex3f(-half,0,half)
    glEnd()

    # Border
    glColor3f(0.4,0.4,0.7)
    glBegin(GL_LINE_LOOP)
    glVertex3f(-half,1,-half); glVertex3f(half,1,-half)
    glVertex3f(half,1,half);   glVertex3f(-half,1,half)
    glEnd()

    # Target
    danger = min(1.0,(level-1)/9.0)
    glColor3f(1.0,1.0-danger*0.8,0.0)
    glPushMatrix(); glTranslatef(target_x,2,target_z); draw_sphere_gl(8,5,8); glPopMatrix()

    # Lander
    glColor3f(1.0,1.0,0.0)
    glPushMatrix(); glTranslatef(lander_x,2,lander_z); draw_sphere_gl(6,5,8); glPopMatrix()

    # Line to target
    glColor3f(0.6,0.6,0.0)
    glBegin(GL_LINES)
    glVertex3f(lander_x,2,lander_z); glVertex3f(target_x,2,target_z)
    glEnd()

    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()

# ═══════════════════════════════════════════════════════════════════════════
#  HUD GAMEPLAY
# ═══════════════════════════════════════════════════════════════════════════
def draw_hud():
    speed = math.sqrt(vel_x**2+vel_y**2+vel_z**2)*60
    dtgt  = math.sqrt((lander_x-target_x)**2+(lander_z-target_z)**2)
    alt   = max(0.0, lander_y-terrain_height(lander_x,lander_z))
    lv = get_land_vel_max(); rad = get_target_radius()
    on_oxy = (fuel<=0 and oxygen>0); both_empty = (fuel<=0 and oxygen<=0)
    blink = abs(math.sin(animation_time*10.0))

    # Left panel
    fc = (1.0,0.55+0.35*blink,0.0) if on_oxy else (1.0,0.1+0.7*blink,0.1) if fuel<10 else (1.0,0.6,0.0) if fuel<30 else (0.2,0.9,0.2)
    draw_text(20, WIN_H-28,  f"FUEL:   {fuel:05.1f}%", *fc)
    oc = (1.0,0.1+0.7*blink,0.1) if oxygen<10 else (1.0,0.75,0.0) if oxygen<30 else (0.2,0.6,1.0)
    draw_text(20, WIN_H-48,  f"OXYGEN: {oxygen:05.1f}%", *oc)

    if both_empty:  draw_text(20,WIN_H-68,"!! NO PROPELLANT - FREE FALL !!",1.0,blink*0.2,blink*0.2)
    elif on_oxy:    draw_text(20,WIN_H-68,"!! OXYGEN BACKUP ACTIVE !!",1.0,0.5+0.4*blink,0.0)
    elif oxygen<15: draw_text(20,WIN_H-68,"!! OXYGEN CRITICAL !!",1.0,blink*0.3,blink*0.3)
    elif fuel<15:   draw_text(20,WIN_H-68,"!! FUEL LOW !!",1.0,0.5+0.4*blink,0.0)

    c2 = (0.0,1.0,0.0) if speed<=lv else (1.0,0.3,0.1)
    draw_text(20, WIN_H-88,  f"SPEED:  {speed:05.2f}  (safe<={lv:.1f})", *c2)
    ac = (0.2,1.0,0.8) if alt>5 else (1.0,0.6,0.0) if alt>2 else (1.0,0.2,0.1)
    draw_text(20, WIN_H-108, f"ALT:    {alt:05.1f} m", *ac)
    draw_text(20, WIN_H-128, f"VEL  X:{vel_x:+.3f} Y:{vel_y:+.3f} Z:{vel_z:+.3f}", 0.6,0.6,0.9)
    dc = (0.0,1.0,0.5) if dtgt<rad*2 else (1.0,1.0,0.3) if dtgt<60 else (0.8,0.8,0.8)
    draw_text(20, WIN_H-148, f"TARGET: {dtgt:05.1f} m  PAD:{rad:.2f}m", *dc)
    draw_text(20, WIN_H-168, "UP=Thrust DN=Retro WASD=Strafe LR=Rotate", 0.4,0.4,0.4)

    # Active keys
    active = []
    if key_up_held():   active.append("^THRUST")
    if key_dn_held():   active.append("vRETRO")
    if key_w_held():    active.append("FWD")
    if key_s_held():    active.append("BACK")
    if key_a_held():    active.append("L-STRAFE")
    if key_d_held():    active.append("R-STRAFE")
    if key_left_held(): active.append("ROT-L")
    if key_right_held():active.append("ROT-R")
    if active:
        p = 0.5+0.5*math.sin(animation_time*12)
        draw_text(WIN_W//2-len(" | ".join(active))*5, WIN_H-28, " | ".join(active), 1.0,0.5+0.5*p,0.0)

    # Right panel
    danger = min(1.0,(level-1)/9.0); lc = (1.0,1.0-danger*0.8,0.0)
    draw_text(WIN_W-210,WIN_H-28, f"SCORE: {score}",     1.0,0.9,0.1)
    draw_text(WIN_W-210,WIN_H-48, f"LEVEL: {level}",     *lc)
    draw_text(WIN_W-210,WIN_H-68, f"PAD R: {rad:.2f}m",  *lc)
    draw_text(WIN_W-210,WIN_H-88, f"MAX V: {lv:.1f}",    *lc)
    draw_text(WIN_W-210,WIN_H-108,f"GRAV:  {diff_gravity():.4f}", 0.6,0.5,0.8)

    # New target flash
    elapsed = animation_time - new_target_flash_start
    if elapsed < 5.0:
        bf = abs(math.sin(animation_time*7)); fade = 1.0-elapsed/5.0
        draw_text(WIN_W//2-160,WIN_H//2+60,f"** NEW TARGET! {dtgt:.0f}m AWAY **",bf*fade,fade,0.0)

    draw_text(20,50,"ESC:MENU  R:RETRY  Q:FULL RESET", 0.4,0.4,0.4)

    # Game over overlay
    if game_over and landing_msg:
        ok = "PERFECT" in landing_msg.upper(); c3 = (0.0,1.0,0.3) if ok else (1.0,0.2,0.1)
        draw_text(WIN_W//2-len(landing_msg)*5, WIN_H//2+20, landing_msg, *c3)
        draw_text(WIN_W//2-200, WIN_H//2-10, "R:RETRY  Q:FULL RESET  ESC:MENU", 0.8,0.8,0.8)
        draw_text(WIN_W//2-100, WIN_H//2-40, f"SCORE:{score}  LEVEL:{level}", 1.0,0.85,0.0)

    if not game_started and not game_over:
        draw_text(WIN_W//2-200,WIN_H//2-30,"HOLD ARROW-UP to lift off!", 0.9,0.9,0.2)

# ═══════════════════════════════════════════════════════════════════════════
#  PHYSICS
# ═══════════════════════════════════════════════════════════════════════════
def update_physics():
    global lander_x,lander_y,lander_z,vel_x,vel_y,vel_z
    global fuel,oxygen,game_over,landing_msg,lander_tilt_z,lander_tilt_x
    global score,level,rocket_heading

    if not game_over:
        if key_left_held():  rocket_heading = (rocket_heading-2.5)%360
        if key_right_held(): rocket_heading = (rocket_heading+2.5)%360

    if game_over or not game_started:
        lander_tilt_z*=0.92; lander_tilt_x*=0.92; return

    G=diff_gravity(); DR=diff_drag(); TU=diff_thrust_up()
    TH=diff_thrust_horiz(); FB=diff_fuel_burn(); MX=diff_max_vel()

    hr  = math.radians(rocket_heading)
    fwx = math.sin(hr); fwz = math.cos(hr)
    rtx = math.cos(hr); rtz = -math.sin(hr)

    vel_y += G
    hf=fuel>0; ho=oxygen>0; oo=(not hf) and ho
    any_key=(key_up_held() or key_dn_held() or
             key_w_held() or key_s_held() or key_a_held() or key_d_held())

    if key_up_held():
        if hf:   vel_y+=TU; fuel=max(0,fuel-FB)
        elif ho: vel_y+=TU*0.55; oxygen=max(0,oxygen-0.10)
    if key_dn_held():
        if hf:   vel_y-=TU*0.45; fuel=max(0,fuel-FB*0.5)
        elif ho: vel_y-=TU*0.25; oxygen=max(0,oxygen-0.06)

    any_strafe=False
    for pressed,ddx,ddz,ta,td in [
        (key_w_held(), +fwx, +fwz, 'x', -1),
        (key_s_held(), -fwx, -fwz, 'x', +1),
        (key_d_held(), +rtx, +rtz, 'z', -1),
        (key_a_held(), -rtx, -rtz, 'z', +1)]:
        if pressed:
            vel_x+=ddx*TH; vel_z+=ddz*TH; any_strafe=True
            if hf:   fuel=max(0,fuel-FB*0.3)
            elif ho: oxygen=max(0,oxygen-0.04)
            if ta=='z': lander_tilt_z=max(-MAX_TILT,min(MAX_TILT,lander_tilt_z+td*TILT_SPEED))
            else:       lander_tilt_x=max(-MAX_TILT,min(MAX_TILT,lander_tilt_x+td*TILT_SPEED))

    if not any_strafe:
        lander_tilt_z*=1.0-TILT_RECOVERY*0.04
        lander_tilt_x*=1.0-TILT_RECOVERY*0.04
    if oo and any_key:
        fuel=min(100,fuel+FUEL_REGEN); oxygen=max(0,oxygen-0.10)

    wx2,wz2=get_wind(); vel_x+=wx2; vel_z+=wz2
    vel_x*=DR; vel_z*=DR
    vel_x=max(-MX,min(MX,vel_x)); vel_z=max(-MX,min(MX,vel_z)); vel_y=max(-MX,min(MX,vel_y))
    lander_x+=vel_x; lander_y+=vel_y; lander_z+=vel_z

    gy=terrain_height(lander_x,lander_z)
    if fuel<=0 and oxygen<=0 and lander_y>gy+0.5:
        landing_msg=f"OUT OF PROPELLANT! Score:{score}"; game_over=True
        vel_x=vel_y=vel_z=0; move_target(); return
    if lander_y<=gy+0.5:
        lander_y=gy+0.5
        speed=math.sqrt(vel_x**2+vel_y**2+vel_z**2)*60
        lv=get_land_vel_max(); rad=get_target_radius()
        dist_hit=math.sqrt((lander_x-target_x)**2+(lander_z-target_z)**2)
        on_target=(dist_hit<=rad)
        if on_target and speed<=lv:
            prec=max(0.0,1.0-dist_hit/rad); mult=1.0+prec
            pts=int(max(1,int(10*level))*mult); score+=pts; level+=1
            landing_msg=f"PERFECT! +{pts}pts (x{mult:.1f}) Speed:{speed:.1f} -> LEVEL {level}!"
        elif on_target:
            landing_msg=f"TOO FAST! Speed:{speed:.1f} (need<={lv:.1f}) Score:{score}"
        else:
            landing_msg=f"CRASHED! {dist_hit:.1f}m from target. Score:{score}"
        move_target(); game_over=True; vel_x=vel_y=vel_z=0

# ═══════════════════════════════════════════════════════════════════════════
#  RESET
# ═══════════════════════════════════════════════════════════════════════════
def reset_game():
    global lander_x,lander_y,lander_z,vel_x,vel_y,vel_z,fuel,oxygen
    global game_started,game_over,landing_msg,gp_cam_pitch
    global lander_tilt_z,lander_tilt_x,rocket_heading
    _clear_keys()
    lander_x=lander_z=0.0; lander_y=terrain_height(0,0)+75.0
    vel_x=vel_y=vel_z=0.0; fuel=oxygen=100.0
    game_started=game_over=False; landing_msg=""
    gp_cam_pitch=22.0; lander_tilt_z=lander_tilt_x=rocket_heading=0.0

def full_reset():
    global score,level
    score=0; level=1; move_target(); reset_game()

# ═══════════════════════════════════════════════════════════════════════════
#  DISPLAY
# ═══════════════════════════════════════════════════════════════════════════
def show_screen():
    glClearColor(0.04,0.04,0.08,1.0)
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    if current_state == "MENU":
        setup_menu_camera()
        draw_menu_scene()
        draw_menu_buttons()

    elif current_state == "ROCKET_LIST":
        setup_menu_camera()
        draw_menu_scene()
        draw_menu_buttons()

    elif current_state == "ROCKET_VIEWER":
        setup_rocket_viewer_camera()
        if   selected_rocket_index==0: draw_jak_hound()
        elif selected_rocket_index==1: draw_eva_nation()
        elif selected_rocket_index==2: draw_jf17_thunder()
        draw_text(20,WIN_H-28,f"INSPECTING: {rocket_list[selected_rocket_index]}",1,1,0)
        sel = (selected_rocket_for_game==selected_rocket_index)
        if sel: draw_text(20,WIN_H-50,"[SELECTED]  F: reselect",0,1,0)
        else:   draw_text(20,WIN_H-50,"Press F to select | ARROWS:rotate | N/M:zoom | ESC:back",0.7,0.7,0.7)

    elif current_state == "GAMEPLAY":
        setup_gameplay_camera()
        draw_space_background()
        draw_terrain()
        draw_target()
        draw_heading_indicator()
        if not game_over:
            draw_trajectory()
        glPushMatrix()
        glTranslatef(lander_x,lander_y,lander_z)
        glRotatef(-rocket_heading,0,1,0)
        glRotatef(lander_tilt_z,0,0,1)
        glRotatef(lander_tilt_x,1,0,0)
        glScalef(1.5,1.5,1.5)
        draw_selected_rocket()
        draw_thrust_flame()
        draw_retro_flame()
        glPopMatrix()
        draw_hud()
        draw_minimap()

    glutSwapBuffers()

# ═══════════════════════════════════════════════════════════════════════════
#  KEYBOARD
# ═══════════════════════════════════════════════════════════════════════════
def keyboard_listener(key, x, y):
    global current_state,selected_option,zoom_level
    global selected_rocket_index,selected_rocket_for_game
    global rocket_selected,show_alert,alert_message

    k = key.lower() if isinstance(key,bytes) else key

    if k == b'\x1b':
        _clear_keys()
        if current_state=="GAMEPLAY":        current_state="MENU";        reset_game()
        elif current_state=="ROCKET_LIST":   current_state="MENU";        selected_option=1; show_alert=False
        elif current_state=="ROCKET_VIEWER": current_state="ROCKET_LIST"; selected_option=selected_rocket_index
        glutPostRedisplay(); return

    if current_state=="GAMEPLAY":
        if k in (b'w',b's',b'a',b'd'): _set_key(k, True)
        if k==b'r': reset_game()
        if k==b'q': full_reset()
        glutPostRedisplay(); return

    if current_state in ["MENU","ROCKET_LIST"]:
        items = main_menu if current_state=="MENU" else rocket_list
        max_opt = len(items)-1
        if k in (b'\r',b' '):
            if current_state=="MENU":
                if selected_option==0: current_state="ROCKET_LIST"; selected_option=0
                elif selected_option==1:
                    current_state="ROCKET_LIST"; selected_option=selected_rocket_for_game if rocket_selected else 0
                elif selected_option==2: _os._exit(0)
            elif current_state=="ROCKET_LIST":
                if 0<=selected_option<3:
                    selected_rocket_index=selected_option; current_state="ROCKET_VIEWER"
                elif selected_option==3:
                    if not rocket_selected: show_alert=True; alert_message="Select a spacecraft first!"
                    else: full_reset(); current_state="GAMEPLAY"

    if current_state=="ROCKET_VIEWER":
        if k==b'n': zoom_level=max(0.3,zoom_level-0.1)
        elif k==b'm': zoom_level=min(3.0,zoom_level+0.1)
        elif k==b'f': selected_rocket_for_game=selected_rocket_index; rocket_selected=True
    glutPostRedisplay()

def keyboard_up_listener(key, x, y):
    k = key.lower() if isinstance(key,bytes) else key
    if current_state=="GAMEPLAY" and k in (b'w',b's',b'a',b'd'):
        _set_key(k, False)

def special_key_listener(key, x, y):
    global cam_rx,cam_ry,selected_option,gp_cam_pitch

    if current_state=="GAMEPLAY":
        if   key==GLUT_KEY_UP:        _set_key(b'\x00up', True)
        elif key==GLUT_KEY_DOWN:      _set_key(b'\x00dn', True)
        elif key==GLUT_KEY_LEFT:      _set_key(b'\x00lt', True)
        elif key==GLUT_KEY_RIGHT:     _set_key(b'\x00rt', True)
        elif key==GLUT_KEY_PAGE_UP:   gp_cam_pitch=min(80,gp_cam_pitch+3)
        elif key==GLUT_KEY_PAGE_DOWN: gp_cam_pitch=max(5,gp_cam_pitch-3)

    elif current_state=="ROCKET_VIEWER":
        if   key==GLUT_KEY_LEFT:  cam_ry-=5
        elif key==GLUT_KEY_RIGHT: cam_ry+=5
        elif key==GLUT_KEY_UP:    cam_rx=min(80,cam_rx+5)
        elif key==GLUT_KEY_DOWN:  cam_rx=max(-80,cam_rx-5)

    elif current_state in ["MENU","ROCKET_LIST"]:
        items = main_menu if current_state=="MENU" else rocket_list
        max_opt = len(items)-1
        if selected_option < 0: selected_option=0
        if   key==GLUT_KEY_UP:   selected_option=max(0,selected_option-1)
        elif key==GLUT_KEY_DOWN: selected_option=min(max_opt,selected_option+1)
    glutPostRedisplay()

def special_up_listener(key, x, y):
    if current_state=="GAMEPLAY":
        if   key==GLUT_KEY_UP:    _set_key(b'\x00up', False)
        elif key==GLUT_KEY_DOWN:  _set_key(b'\x00dn', False)
        elif key==GLUT_KEY_LEFT:  _set_key(b'\x00lt', False)
        elif key==GLUT_KEY_RIGHT: _set_key(b'\x00rt', False)

def mouse_listener(button, state, x, y):
    global current_state,selected_option,selected_rocket_index
    global last_click_x,last_click_y,rocket_selected,show_alert,alert_message

    if button==GLUT_LEFT_BUTTON and state==GLUT_DOWN:
        last_click_x,last_click_y=x,y; ly=WIN_H-y
        if current_state in ["MENU","ROCKET_LIST"]:
            items = main_menu if current_state=="MENU" else rocket_list
            for i,label in enumerate(items):
                cy = 500 - i*80
                if abs(ly - cy) < 20:
                    if selected_option==i:
                        if current_state=="MENU":
                            if i==0: current_state="ROCKET_LIST"; selected_option=0
                            elif i==1: current_state="ROCKET_LIST"; selected_option=selected_rocket_for_game if rocket_selected else 0
                            elif i==2: _os._exit(0)
                        elif current_state=="ROCKET_LIST":
                            if 0<=i<3: selected_rocket_index=i; current_state="ROCKET_VIEWER"
                            elif i==3:
                                if not rocket_selected: show_alert=True; alert_message="Select a spacecraft first!"
                                else: full_reset(); current_state="GAMEPLAY"
                    else: selected_option=i
        elif current_state=="ROCKET_VIEWER":
            if ly < 80: current_state="ROCKET_LIST"
    glutPostRedisplay()

# ═══════════════════════════════════════════════════════════════════════════
#  IDLE
# ═══════════════════════════════════════════════════════════════════════════
def idle():
    global animation_time, planet_rotation_y
    animation_time += 0.01
    planet_rotation_y += 0.015
    if current_state=="GAMEPLAY":
        update_physics()
    glutPostRedisplay()

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Lunar Descent")

    glEnable(GL_DEPTH_TEST)

    glutDisplayFunc(show_screen)
    glutKeyboardFunc(keyboard_listener)
    glutKeyboardUpFunc(keyboard_up_listener)
    glutSpecialFunc(special_key_listener)
    glutSpecialUpFunc(special_up_listener)
    glutMouseFunc(mouse_listener)
    glutIdleFunc(idle)
    glutIgnoreKeyRepeat(1)

    move_target()
    reset_game()
    glutMainLoop()

if __name__ == "__main__":
    main()