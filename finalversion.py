from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLUT import GLUT_BITMAP_9_BY_15, GLUT_BITMAP_HELVETICA_18
from OpenGL.GLU import gluSphere, gluNewQuadric, gluCylinder, gluDisk
import math, random, os as _os, time

WIN_W, WIN_H = 1200, 900

# ── Global State ────────────────────────────────────────────────────────────
current_state            = "MENU"
selected_option          = -1
selected_rocket_index    = 0
selected_rocket_for_game = -1
rocket_selected          = False
show_alert               = False
alert_message            = ""
last_click_x, last_click_y = -1000, -1000
animation_time           = 0.0
planet_rotation_y        = 0.0
frame_count              = 0
last_frame_time          = 0.0
dt                       = 0.016          # delta-time seconds
screen_shake             = 0.0           # trauma value 0-1
shake_x = shake_y        = 0.0

cam_rx, cam_ry = 15.0, 0.0
zoom_level     = 1.0
tutorial_scroll = 0

main_menu    = ["START GAME", "OPTIONS", "QUIT"]
options_menu = ["TUTORIAL", "CHECK ROCKET", "BACK"]
rocket_list  = ["JakHound F-22", "EvaNation F-15", "JF17 Thunder", "START MISSION"]

tutorial_text = [
    "LUNAR DESCENT - How to Play","",
    "GAME OVERVIEW",
    "Pilot a rocket to safely land on the lunar surface. Manage",
    "limited fuel and oxygen resources while navigating treacherous",
    "terrain. Achieve perfect landings to advance through levels.","",
    "BASIC CONTROLS",
    "SPACE - Main Thrust (uses fuel, switches to oxygen when empty)",
    "DOWN ARROW - Retro-thrust (slows descent, uses less fuel)",
    "W/A/S/D - Move forward/left/backward/right (combine for diagonals)",
    "LEFT/RIGHT ARROWS - Rotate camera around lander",
    "PAGE UP/PAGE DOWN - Adjust camera pitch",
    "C - Toggle autopilot (auto-lands if possible)","",
    "RESOURCE MANAGEMENT",
    "FUEL (Primary) - Starts at 100%, regenerates when idle",
    "OXYGEN (Backup) - Activates when fuel depletes (55% efficiency)",
    "When both empty: Free fall with no recovery possible!","",
    "LANDING OBJECTIVES",
    "Land INSIDE the orange target rings (cyan on minimap)",
    "Land at or BELOW the safe speed (shown in green in HUD)",
    "Speed requirements get stricter at higher levels",
    "PERFECT LANDING = On target + Safe speed = More points + Level up","",
    "LANDING OUTCOMES",
    "PERFECT! - On target + safe speed (earn bonus, advance level)",
    "TOO FAST! - On target but exceeding speed limit (mission failed)",
    "CRASHED! - Landed outside target zone (mission failed)","",
    "SCORING SYSTEM",
    "Base Points = 10 x Current_Level",
    "Precision Bonus = 1.0x (pad edge) to 2.0x (pad center)",
    "Final Score = Base x Multiplier","",
    "QUICK CHECKLIST",
    "1. Select your rocket from the menu",
    "2. Practice on lower levels first",
    "3. Master thrust + horizontal movement combinations",
    "4. Learn to use retro-thrust efficiently",
    "5. Aim for PERFECT! landings for bonus points",
    "6. Progress to harder levels","",
    "READY TO FLY? ESC to return to menu and start your mission!",
    "May your landings be smooth and your fuel abundant!"
]

# ── Lander ──────────────────────────────────────────────────────────────────
lander_x = 0.0; lander_y = 80.0; lander_z = 0.0
vel_x = vel_y = vel_z = 0.0
fuel = 100.0; oxygen = 100.0
game_started = False; game_over = False; landing_msg = ""
lander_tilt_z = lander_tilt_x = rocket_heading = 0.0
gp_cam_pitch = 22.0; gp_cam_dist = 45.0; gp_cam_yaw = 0.0

score = 0; level = 1
target_x = target_z = 0.0; target_surface_y = 0.0
new_target_flash_start = -999.0
MAX_TILT = 40.0; TILT_SPEED = 1.6; TILT_RECOVERY = 2.8; FUEL_REGEN = 0.28
autopilot = False

KEY_WINDOW    = 6
key_last_seen = {}

# ── Particles ────────────────────────────────────────────────────────────────
particles = []   # list of dicts

def spawn_exhaust(x, y, z, count=6, is_oxy=False, retro=False):
    for _ in range(count):
        spread = 0.18
        vx = random.uniform(-spread, spread)
        vy = random.uniform(-0.35, -0.05) if not retro else random.uniform(0.1, 0.45)
        vz = random.uniform(-spread, spread)
        if is_oxy:
            col = (random.uniform(0.3,0.6), random.uniform(0.5,0.9), 1.0)
        else:
            r = random.uniform(0.9,1.0); g = random.uniform(0.3,0.7)
            col = (r, g, 0.0)
        particles.append({
            'x': x + random.uniform(-0.2,0.2),
            'y': y,
            'z': z + random.uniform(-0.2,0.2),
            'vx': vx, 'vy': vy, 'vz': vz,
            'life': random.uniform(0.3, 0.7),
            'max_life': 0.6,
            'size': random.uniform(0.8, 2.2),
            'col': col
        })

def spawn_impact(x, y, z, count=40):
    for _ in range(count):
        speed = random.uniform(0.05, 0.5)
        ang = random.uniform(0, 2*math.pi)
        el  = random.uniform(0, math.pi*0.5)
        particles.append({
            'x': x, 'y': y, 'z': z,
            'vx': math.cos(ang)*math.cos(el)*speed,
            'vy': math.sin(el)*speed,
            'vz': math.sin(ang)*math.cos(el)*speed,
            'life': random.uniform(0.5,1.5),
            'max_life': 1.5,
            'size': random.uniform(1.0,3.5),
            'col': (random.uniform(0.6,1.0), random.uniform(0.3,0.6), 0.0)
        })

def update_particles():
    global particles
    alive = []
    for p in particles:
        p['life'] -= dt
        if p['life'] <= 0:
            continue
        p['x'] += p['vx']
        p['y'] += p['vy']
        p['z'] += p['vz']
        p['vy'] -= 0.002   # tiny gravity on particles
        alive.append(p)
    particles = alive

def draw_particles():
    if not particles:
        return
    glDepthMask(GL_FALSE)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glBegin(GL_QUADS)
    for p in particles:
        alpha = max(0.0, p['life'] / p['max_life'])
        r, g, b = p['col']
        sz = p['size'] * alpha
        glColor4f(r, g, b, alpha * 0.85)
        # billboard quad (always faces camera – approximated as screen-aligned)
        glVertex3f(p['x']-sz*0.05, p['y'],       p['z'])
        glVertex3f(p['x'],         p['y']+sz*0.05,p['z'])
        glVertex3f(p['x']+sz*0.05, p['y'],       p['z'])
        glVertex3f(p['x'],         p['y']-sz*0.05,p['z'])
    glEnd()
    glDisable(GL_BLEND)
    glDepthMask(GL_TRUE)

# ── Keys ─────────────────────────────────────────────────────────────────────
def _key_press(token):
    global game_started
    key_last_seen[token] = frame_count
    if current_state == "GAMEPLAY":
        game_started = True

def key_held(token):
    return key_last_seen.get(token, -9999) >= frame_count - KEY_WINDOW

def key_space_held(): return key_held(b'\x00sp')
def key_dn_held():    return key_held(b'\x00dn')
def key_w_held():     return key_held(b'w')
def key_s_held():     return key_held(b's')
def key_a_held():     return key_held(b'a')
def key_d_held():     return key_held(b'd')
def key_left_held():  return key_held(b'\x00lt')
def key_right_held(): return key_held(b'\x00rt')

# ── Difficulty ───────────────────────────────────────────────────────────────
def diff_gravity():      return max(-0.016, -0.007  - (level-1)*0.00075)
def diff_drag():         return max(0.945,   0.980  - (level-1)*0.0038)
def diff_thrust_up():    return 0.070
def diff_thrust_horiz(): return 0.010
def diff_max_vel():      return 0.75
def diff_fuel_burn():    return max(0.09, 0.13 + (level-1)*0.004)
def get_land_vel_max():  return max(4.5,  22.0 - (level-1)*1.8)
def get_target_radius(): return max(0.8,   6.5 - (level-1)*0.60)
def get_wind():
    if level < 4: return 0.0, 0.0
    s = (level-3)*0.00028; a = math.radians(animation_time*4.0)
    return math.cos(a)*s, math.sin(a)*s

# ── Terrain ──────────────────────────────────────────────────────────────────
WORLD_HALF   = 320
TERRAIN_DIVS = 100          # increased from 90
_terrain_dl  = None
_mountains   = []
_craters     = []
_terrain_tris = []

def terrain_height(wx, wz):
    y = 0.0
    for (cx, cz, rad, pk) in _mountains:
        d = math.sqrt((wx-cx)**2 + (wz-cz)**2)
        if d < rad:
            t = 1.0 - d/rad; y += pk*t*t*(3.0-2.0*t)
    for (cx, cz, rad, dep) in _craters:
        d = math.sqrt((wx-cx)**2 + (wz-cz)**2)
        if d < rad:
            t = d/rad
            y += -dep*(1.0-t*t) + dep*0.42*math.exp(-((t-0.86)/0.07)**2)
    return y

def _build_terrain_dl():
    global _terrain_dl, _terrain_tris
    step = (WORLD_HALF*2)/TERRAIN_DIVS; cols = TERRAIN_DIVS+1
    verts = []
    for row in range(cols):
        for col in range(cols):
            wx = -WORLD_HALF + col*step; wz = -WORLD_HALF + row*step
            verts.append((wx, terrain_height(wx, wz), wz))

    # Pre-compute smooth per-vertex normals
    normals = [(0.0,0.0,0.0)] * len(verts)
    for row in range(TERRAIN_DIVS):
        for col in range(TERRAIN_DIVS):
            i00=row*cols+col; i10=i00+1; i01=i00+cols; i11=i01+1
            def tri_normal(ia, ib, ic):
                va,vb,vc = verts[ia],verts[ib],verts[ic]
                ux,uy,uz = vb[0]-va[0],vb[1]-va[1],vb[2]-va[2]
                vx2,vy2,vz2 = vc[0]-va[0],vc[1]-va[1],vc[2]-va[2]
                nx=uy*vz2-uz*vy2; ny=uz*vx2-ux*vz2; nz2=ux*vy2-uy*vx2
                ln=math.sqrt(nx*nx+ny*ny+nz2*nz2)
                if ln>1e-9: nx/=ln; ny/=ln; nz2/=ln
                return (nx,ny,nz2)
            for idx_set in [(i00,i10,i01),(i10,i11,i01)]:
                n = tri_normal(*idx_set)
                for idx in idx_set:
                    nx2,ny2,nz2 = normals[idx]
                    normals[idx] = (nx2+n[0], ny2+n[1], nz2+n[2])

    # Normalize accumulated normals
    norm_vn = []
    for nx2,ny2,nz2 in normals:
        ln = math.sqrt(nx2*nx2+ny2*ny2+nz2*nz2)
        if ln>1e-9: norm_vn.append((nx2/ln,ny2/ln,nz2/ln))
        else:       norm_vn.append((0,1,0))

    # Build display list
    if _terrain_dl is not None:
        glDeleteLists(_terrain_dl, 1)
    _terrain_dl = glGenLists(1)
    glNewList(_terrain_dl, GL_COMPILE)
    glBegin(GL_TRIANGLES)
    for row in range(TERRAIN_DIVS):
        for col in range(TERRAIN_DIVS):
            i00=row*cols+col; i10=i00+1; i01=i00+cols; i11=i01+1
            def emit(ia, ib, ic):
                for idx in (ia,ib,ic):
                    avg_y = verts[idx][1]
                    t=max(0.0,min(1.0,(avg_y+18)/62.0)); b=0.18+t*0.36
                    glColor3f(b*0.96, b, b*1.06)
                    glNormal3f(*norm_vn[idx])
                    glVertex3f(*verts[idx])
            emit(i00,i10,i01); emit(i10,i11,i01)
    glEnd()
    glEndList()

    # Also keep CPU list for trajectory collision
    _terrain_tris = []
    for row in range(TERRAIN_DIVS):
        for col in range(TERRAIN_DIVS):
            i00=row*cols+col; i10=i00+1; i01=i00+cols; i11=i01+1
            for ia,ib,ic in [(i00,i10,i01),(i10,i11,i01)]:
                _terrain_tris.append((verts[ia],verts[ib],verts[ic]))

def generate_terrain():
    global _mountains, _craters
    rng = random.Random(level*31+7)
    _mountains = []
    for i in range(22+level*2):
        _mountains.append((rng.uniform(-WORLD_HALF+20,WORLD_HALF-20),
                           rng.uniform(-WORLD_HALF+20,WORLD_HALF-20),
                           rng.uniform(28,85), rng.uniform(18,55)))
    for i in range(6+level):
        _mountains.append((rng.uniform(-WORLD_HALF+40,WORLD_HALF-40),
                           rng.uniform(-WORLD_HALF+40,WORLD_HALF-40),
                           rng.uniform(20,45), rng.uniform(55,90)))
    _craters = []
    for i in range(30+level*2):
        _craters.append((rng.uniform(-WORLD_HALF+10,WORLD_HALF-10),
                         rng.uniform(-WORLD_HALF+10,WORLD_HALF-10),
                         rng.uniform(8,42), rng.uniform(5,20)))
    for i in range(4):
        _craters.append((rng.uniform(-WORLD_HALF+60,WORLD_HALF-60),
                         rng.uniform(-WORLD_HALF+60,WORLD_HALF-60),
                         rng.uniform(50,90), rng.uniform(18,32)))
    _build_terrain_dl()

def move_target():
    global target_x,target_z,target_surface_y,new_target_flash_start
    rng = random.Random(level*17+score*3+int(animation_time*100))
    spread = min(WORLD_HALF-30, 80+level*9)
    for i in range(800):
        a=rng.uniform(0,2*math.pi); d=rng.uniform(max(80,spread*0.55),spread)
        tx=math.cos(a)*d; tz=math.sin(a)*d
        if abs(tx)<WORLD_HALF-15 and abs(tz)<WORLD_HALF-15:
            target_x,target_z=tx,tz; break
    target_surface_y=terrain_height(target_x,target_z)
    new_target_flash_start=animation_time
    generate_terrain()

# ── Lighting ─────────────────────────────────────────────────────────────────
def setup_lighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightModelf(GL_LIGHT_MODEL_TWO_SIDE, 1.0)

    # Sun – warm directional
    glLightfv(GL_LIGHT0, GL_POSITION,  [1.0, 2.0, 1.0, 0.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE,   [1.0, 0.95, 0.85, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR,  [0.6, 0.55, 0.45, 1.0])
    glLightfv(GL_LIGHT0, GL_AMBIENT,   [0.04, 0.04, 0.08, 1.0])

    # Fill light – cool blue from below
    glLightfv(GL_LIGHT1, GL_POSITION,  [-0.5, -1.0, 0.5, 0.0])
    glLightfv(GL_LIGHT1, GL_DIFFUSE,   [0.08, 0.10, 0.20, 1.0])
    glLightfv(GL_LIGHT1, GL_SPECULAR,  [0.0,  0.0,  0.0,  1.0])
    glLightfv(GL_LIGHT1, GL_AMBIENT,   [0.0,  0.0,  0.0,  1.0])

    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,  [0.3, 0.3, 0.3, 1.0])
    glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, 28.0)

def disable_lighting():
    glDisable(GL_LIGHTING)

# ── Projection & Camera ───────────────────────────────────────────────────────
def set_perspective(fovy_deg, aspect, znear, zfar):
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    f = 1.0/math.tan(math.radians(fovy_deg)*0.5)
    top=znear/f; bottom=-top; right=top*aspect; left=-right
    rl=(right-left); tb=(top-bottom); fn=(zfar-znear)
    if rl==0 or tb==0 or fn==0: return
    m=[
        (2.0*znear)/rl, 0.0, 0.0, 0.0,
        0.0, (2.0*znear)/tb, 0.0, 0.0,
        (right+left)/rl, (top+bottom)/tb, -(zfar+znear)/fn, -1.0,
        0.0, 0.0, -(2.0*zfar*znear)/fn, 0.0
    ]
    glLoadMatrixf(m)

def set_camera(ex,ey,ez,cx,cy,cz):
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    fx=cx-ex; fy=cy-ey; fz=cz-ez
    fl=math.sqrt(fx*fx+fy*fy+fz*fz)
    if fl<1e-9: return
    fx/=fl; fy/=fl; fz/=fl
    yaw  =math.degrees(math.atan2(-fx,-fz))
    pitch=math.degrees(math.asin(max(-1.0,min(1.0,fy))))
    glRotatef(-pitch,1,0,0); glRotatef(-yaw,0,1,0)
    glTranslatef(-ex,-ey,-ez)

def _ortho_push():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    glScalef(2.0/WIN_W, 2.0/WIN_H, -0.001)
    glTranslatef(-WIN_W/2.0, -WIN_H/2.0, 0.0)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()

def _ortho_pop():
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()

# ── GL Primitives (with normals) ─────────────────────────────────────────────
_quadric = None

def get_quadric():
    global _quadric
    if _quadric is None:
        _quadric = gluNewQuadric()
    return _quadric

def draw_cylinder(r, h, sides=20):
    q = get_quadric()
    gluCylinder(q, r, r, h, sides, 2)
    # caps
    glPushMatrix()
    glRotatef(180,1,0,0)
    gluDisk(q, 0, r, sides, 1)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0,0,h)
    gluDisk(q, 0, r, sides, 1)
    glPopMatrix()

def draw_cone(r, h, sides=20):
    q = get_quadric()
    gluCylinder(q, r, 0, h, sides, 2)
    glPushMatrix()
    glRotatef(180,1,0,0)
    gluDisk(q, 0, r, sides, 1)
    glPopMatrix()

def draw_sphere(r, stacks=12, slices=18):
    q = get_quadric()
    gluSphere(q, r, slices, stacks)

def draw_box(sx, sy, sz):
    hx,hy,hz=sx/2,sy/2,sz/2
    faces = [
        ([(hx,hy,hz),(hx,-hy,hz),(hx,-hy,-hz),(hx,hy,-hz)],(1,0,0)),
        ([(-hx,hy,-hz),(-hx,-hy,-hz),(-hx,-hy,hz),(-hx,hy,hz)],(-1,0,0)),
        ([(-hx,hy,-hz),(hx,hy,-hz),(hx,hy,hz),(-hx,hy,hz)],(0,1,0)),
        ([(-hx,-hy,hz),(hx,-hy,hz),(hx,-hy,-hz),(-hx,-hy,-hz)],(0,-1,0)),
        ([(-hx,hy,hz),(hx,hy,hz),(hx,-hy,hz),(-hx,-hy,hz)],(0,0,1)),
        ([(hx,hy,-hz),(-hx,hy,-hz),(-hx,-hy,-hz),(hx,-hy,-hz)],(0,0,-1))
    ]
    glBegin(GL_QUADS)
    for vts,nm in faces:
        glNormal3f(*nm)
        for v in vts: glVertex3f(*v)
    glEnd()

def draw_disk(r, sides=20):
    q = get_quadric()
    gluDisk(q, 0, r, sides, 1)

# ── Text & Buttons ────────────────────────────────────────────────────────────
def draw_text(x, y, text, r, g, b, font=GLUT_BITMAP_9_BY_15):
    glColor3f(r,g,b); tx=x
    for ch in text:
        glRasterPos2f(tx,y); glutBitmapCharacter(font,ord(ch)); tx+=9

def draw_text18(x, y, text, r, g, b):
    glColor3f(r,g,b); tx=x
    for ch in text:
        glRasterPos2f(tx,y); glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18,ord(ch)); tx+=11

def draw_button(x, y, text, index):
    global selected_option
    tw=len(text)*10; x0,x1=x-tw/2-20,x+tw/2+20; y0,y1=y-10,y+25
    gl_y=WIN_H-last_click_y
    if x0<=last_click_x<=x1 and y0<=gl_y<=y1: selected_option=index
    sel=(selected_option==index)
    # Glow background
    if sel:
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.9,0.1,0.1,0.25)
        glBegin(GL_QUADS)
        glVertex2f(x0,y0); glVertex2f(x1,y0); glVertex2f(x1,y1); glVertex2f(x0,y1)
        glEnd(); glDisable(GL_BLEND)
        draw_text18(x-tw/2,y+2,text,1,1,1)
        glColor3f(1.0,0.2,0.2)
    else:
        draw_text18(x-tw/2,y+2,text,0.7,0.1,0.1)
        glColor3f(0.35,0,0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x0,y0); glVertex2f(x1,y0); glVertex2f(x1,y1); glVertex2f(x0,y1)
    glEnd()

# ── Menu Background ───────────────────────────────────────────────────────────
star_data=[]
for i in range(800):
    _tx,_ty=random.uniform(-100,100),random.uniform(-60,60)
    star_data.append([_tx,_ty,random.uniform(-150,-20),random.uniform(0.5,1.0),_tx,_ty])

def draw_interactive_scene():
    set_perspective(45,WIN_W/WIN_H,0.1,600.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    glTranslatef(0,0,-60)
    glPointSize(2.5); glBegin(GL_POINTS)
    mx=(last_click_x-WIN_W/2)/6.0; my=(WIN_H/2-last_click_y)/6.0
    for i,s in enumerate(star_data):
        blink=0.3+0.7*abs(math.sin(animation_time*3+i*0.7))
        glColor3f(blink*s[3],blink*s[3],blink*s[3]*1.05)
        dx,dy=mx-s[0],my-s[1]; dist=math.sqrt(dx**2+dy**2)
        if dist<15: s[0]+=dx*0.04; s[1]+=dy*0.04
        else:       s[0]+=(s[4]-s[0])*0.015; s[1]+=(s[5]-s[1])*0.015
        glVertex3f(s[0],s[1],s[2])
    glEnd()
    # Moon
    glPushMatrix()
    glTranslatef(22,-14,15)
    glRotatef(planet_rotation_y+(last_click_x-WIN_W/2)/40.0,0,1,0)
    glRotatef((last_click_y-WIN_H/2)/40.0,1,0,0)
    glColor3f(0.80,0.80,0.82); draw_sphere(8,20,28)
    glPushMatrix(); glRotatef(animation_time*8,1,1,0)
    glColor3f(0.28,0.28,0.31); draw_sphere(8.05,8,12); glPopMatrix()
    glPopMatrix()

# ── Rocket Models ─────────────────────────────────────────────────────────────
def draw_jak_hound():
    glPushMatrix(); glRotatef(-90,1,0,0)   # align Y-up → GLU Z-up

    glColor3f(0.14,0.14,0.16); draw_cylinder(0.30,2.10,16)
    glColor3f(0.85,0.60,0.10)
    glPushMatrix(); glTranslatef(0,0,1.65); draw_cylinder(0.31,0.22,16); glPopMatrix()

    glColor3f(0.05,0.55,0.95)
    glPushMatrix(); glTranslatef(0.33,0,1.52); draw_sphere(0.09,8,10); glPopMatrix()

    glColor3f(0.75,0.55,0.08)
    for pz in [0.30,0.65,1.00,1.35]:
        glPushMatrix(); glTranslatef(0.29,0,pz); draw_box(0.04,0.34,0.025); glPopMatrix()

    glColor3f(0.18,0.18,0.20)
    glPushMatrix(); glTranslatef(0,0,2.10); draw_cone(0.28,0.95,16); glPopMatrix()

    glColor3f(0.80,0.60,0.10)
    glPushMatrix(); glTranslatef(0,0,3.05); draw_sphere(0.07,8,10); glPopMatrix()

    glColor3f(0.12,0.12,0.14)
    glPushMatrix(); glRotatef(180,1,0,0); draw_disk(0.32,16); glPopMatrix()

    for i in range(4):
        glPushMatrix(); glRotatef(i*90,0,0,1)
        glColor3f(0.12,0.12,0.14)
        glTranslatef(0.30,0,0.10); draw_box(0.05,0.40,0.65); glPopMatrix()
        glPushMatrix(); glRotatef(i*90,0,0,1)
        glColor3f(0.75,0.55,0.08)
        glTranslatef(0.50,0,0.10); draw_box(0.055,0.04,0.65); glPopMatrix()

    glColor3f(0.20,0.20,0.22)
    glPushMatrix(); glTranslatef(0,0,-0.28); glRotatef(180,1,0,0); draw_cylinder(0.20,0.28,16); glPopMatrix()
    glColor3f(0.75,0.55,0.08)
    glPushMatrix(); glRotatef(180,1,0,0); draw_disk(0.22,16); glPopMatrix()

    glPopMatrix()

def draw_eva_nation():
    glPushMatrix(); glRotatef(-90,1,0,0)

    glColor3f(0.95,0.55,0.75); draw_cylinder(0.40,2.2,20)
    glColor3f(0.97,0.97,0.97)
    glPushMatrix(); glTranslatef(0.42,0,0.8); draw_box(0.05,0.28,0.70); glPopMatrix()
    glColor3f(0.85,0.72,0.30)
    for pz in [0.5,0.9,1.30]:
        glPushMatrix(); glTranslatef(0.42,0,pz); draw_box(0.06,0.30,0.04); glPopMatrix()
    glColor3f(0.90,0.40,0.65)
    glPushMatrix(); glTranslatef(0,0,2.2); draw_cone(0.38,1.10,20); glPopMatrix()
    glColor3f(1.0,0.80,0.90)
    glPushMatrix(); glTranslatef(0,0,3.30); draw_sphere(0.08,8,10); glPopMatrix()
    glColor3f(0.85,0.45,0.70)
    glPushMatrix(); glRotatef(180,1,0,0); draw_disk(0.42,20); glPopMatrix()
    for i,col in enumerate([(0.80,0.35,0.60),(0.90,0.45,0.70),(0.80,0.35,0.60),(0.90,0.45,0.70)]):
        glColor3f(*col); glPushMatrix(); glRotatef(i*90,0,0,1)
        glTranslatef(0.38,0,0.10); draw_box(0.06,0.55,0.85); glPopMatrix()
    glColor3f(0.55,0.15,0.80)
    glPushMatrix(); glTranslatef(0,0,0.05); draw_cylinder(0.44,0.05,32); glPopMatrix()

    glPopMatrix()

def draw_jf17_thunder():
    glPushMatrix(); glRotatef(-90,1,0,0)

    glColor3f(0.55,0.05,0.05); draw_cylinder(0.32,2.0,12)
    glColor3f(0.70,0.08,0.08)
    for pz,sz in [(1.50,0.30),(0.90,0.28),(0.35,0.28)]:
        glPushMatrix(); glTranslatef(0.33,0,pz); draw_box(0.05,0.24,sz); glPopMatrix()
    glColor3f(1.0,0.20,0.05)
    for pz in [0.20,0.60,1.00,1.40,1.80]:
        glPushMatrix(); glTranslatef(0.31,0,pz); draw_box(0.04,0.30,0.03); glPopMatrix()
    glColor3f(0.65,0.07,0.07)
    glPushMatrix(); glTranslatef(0,0,2.0); draw_cone(0.30,0.90,12); glPopMatrix()
    glColor3f(0.9,0.3,0.3)
    glPushMatrix(); glTranslatef(0,0,2.90); draw_sphere(0.06,8,10); glPopMatrix()
    glColor3f(0.45,0.04,0.04)
    glPushMatrix(); glRotatef(180,1,0,0); draw_disk(0.34,12); glPopMatrix()
    for i in range(4):
        glColor3f(0.50,0.05,0.05); glPushMatrix(); glRotatef(i*90,0,0,1)
        glTranslatef(0.44,0,0.15); draw_box(0.06,0.40,0.70); glPopMatrix()

    glPopMatrix()

def draw_selected_rocket():
    if   selected_rocket_for_game==0: draw_jak_hound()
    elif selected_rocket_for_game==1: draw_eva_nation()
    elif selected_rocket_for_game==2: draw_jf17_thunder()
    else: draw_jak_hound()

# ── Space Background ──────────────────────────────────────────────────────────
def draw_space_background():
    disable_lighting()
    glPointSize(2.0); glBegin(GL_POINTS)
    random.seed(7)
    for i in range(600):
        ang=random.uniform(0,2*math.pi); el=random.uniform(-math.pi/2,math.pi/2)
        br=random.uniform(0.6,1.0)
        glColor3f(br,br,br*1.05)
        glVertex3f(450*math.cos(el)*math.cos(ang),450*math.sin(el),450*math.cos(el)*math.sin(ang))
    glEnd()
    # Distant sun / planet
    glPushMatrix(); glRotatef(planet_rotation_y*0.1,0,1,0); glTranslatef(400,100,0)
    glColor3f(1.0,0.9,0.3); draw_sphere(22,12,18); glPopMatrix()
    # Blue planet with cloud shell
    glPushMatrix(); glRotatef(planet_rotation_y*0.3,0,1,0); glTranslatef(260,40,-130)
    glColor3f(0.1,0.4,0.8); draw_sphere(12,10,16)
    glColor3f(0.9,0.9,0.9); glPushMatrix(); glRotatef(planet_rotation_y*2,0,1,0)
    draw_sphere(12.3,5,8); glPopMatrix(); glPopMatrix()
    # Red planet
    glPushMatrix(); glRotatef(planet_rotation_y*0.2,0,1,0); glTranslatef(-220,-25,180)
    glColor3f(0.7,0.25,0.1); draw_sphere(7,8,12); glPopMatrix()
    setup_lighting()

def draw_terrain():
    if _terrain_dl:
        glCallList(_terrain_dl)

# ── Target & Indicators ───────────────────────────────────────────────────────
def draw_target():
    cx,cz=target_x,target_z; sy=terrain_height(cx,cz)
    rad=get_target_radius(); pulse=0.5+0.5*math.sin(animation_time*4.0)
    danger=min(1.0,(level-1)/9.0); tg=1.0-danger*0.8

    disable_lighting()
    # Outer glow rings
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE)
    for ring_r,alpha in [(rad+3.0,0.18),(rad+1.5,0.28),(rad,0.55),(rad*0.5,0.7)]:
        glColor4f(1.0,tg*(pulse*0.8+0.2),0.0,alpha*pulse)
        glBegin(GL_LINE_LOOP)
        for s in range(64):
            a=2*math.pi*s/64
            wx2=cx+ring_r*math.cos(a); wz2=cz+ring_r*math.sin(a)
            glVertex3f(wx2,terrain_height(wx2,wz2)+0.12,wz2)
        glEnd()
    glDisable(GL_BLEND)

    glColor3f(1.0,tg,0.0)
    glBegin(GL_LINES)
    glVertex3f(cx-(rad+3),sy+0.15,cz); glVertex3f(cx+(rad+3),sy+0.15,cz)
    glVertex3f(cx,sy+0.15,cz-(rad+3)); glVertex3f(cx,sy+0.15,cz+(rad+3))
    glEnd()

    # Rotating tick marks
    glColor3f(1.0,0.6,0.0)
    for tick in range(8):
        a=2*math.pi*tick/8+animation_time*0.8
        glBegin(GL_LINES)
        glVertex3f(cx+rad*0.75*math.cos(a),sy+0.15,cz+rad*0.75*math.sin(a))
        glVertex3f(cx+rad*1.12*math.cos(a),sy+0.15,cz+rad*1.12*math.sin(a))
        glEnd()

    # Beacon beam
    bh=sy+40.0+pulse*6.0
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE)
    glColor4f(1.0,tg,0.0,0.25*pulse)
    glBegin(GL_LINES); glVertex3f(cx,sy+0.1,cz); glVertex3f(cx,bh,cz); glEnd()
    glDisable(GL_BLEND)
    glColor3f(1.0,tg,0.0)
    glBegin(GL_LINES); glVertex3f(cx,sy+0.1,cz); glVertex3f(cx,bh,cz); glEnd()
    glPointSize(12.0); glColor3f(1.0,1.0,0.2*pulse)
    glBegin(GL_POINTS); glVertex3f(cx,bh,cz); glEnd()
    glPointSize(1.0)
    setup_lighting()

def draw_new_target_arrow():
    elapsed=animation_time-new_target_flash_start
    if elapsed>5.0: return
    fade=1.0-elapsed/5.0; alpha=fade*abs(math.sin(animation_time*8.0))
    dx=target_x-lander_x; dz=target_z-lander_z
    dist=math.sqrt(dx**2+dz**2)
    if dist<0.01: return
    nx2=dx/dist; nz2=dz/dist
    ax=lander_x+nx2*8; az=lander_z+nz2*8; ay=lander_y+3.0
    disable_lighting()
    glColor3f(alpha,alpha*0.85,0.0)
    glBegin(GL_LINES); glVertex3f(lander_x,ay,lander_z); glVertex3f(ax,ay,az); glEnd()
    glPointSize(14.0); glBegin(GL_POINTS); glVertex3f(ax,ay,az); glEnd()
    glPointSize(1.0)
    setup_lighting()

def draw_heading_indicator():
    sy=terrain_height(lander_x,lander_z)
    hr=math.radians(rocket_heading)
    ex2=lander_x+math.sin(hr)*6; ez2=lander_z+math.cos(hr)*6
    disable_lighting()
    glColor3f(0.0,1.0,1.0)
    glBegin(GL_LINES)
    glVertex3f(lander_x,sy+0.35,lander_z)
    glVertex3f(ex2,terrain_height(ex2,ez2)+0.35,ez2)
    glEnd()
    setup_lighting()

def draw_thrust_flame():
    if not key_space_held(): return
    if fuel<=0 and oxygen<=0: return
    on_oxy=(fuel<=0 and oxygen>0)
    flame=0.5+0.5*math.sin(animation_time*18.0)
    disable_lighting()
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE)
    if on_oxy:
        glColor4f(0.4,0.6+0.3*flame,1.0,0.82)
    else:
        glColor4f(1.0,0.5+0.3*flame,0.0,0.85)
    glPushMatrix(); glTranslatef(0,-0.5,0); glRotatef(180,1,0,0)
    draw_cone(0.35,1.2+0.7*flame,16)
    glPopMatrix()
    glDisable(GL_BLEND)
    setup_lighting()

def draw_retro_flame():
    if not key_dn_held() or (fuel<=0 and oxygen<=0): return
    flame=0.4+0.4*math.sin(animation_time*18.0)
    disable_lighting()
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE)
    glColor4f(0.5,0.8+0.2*flame,1.0,0.75)
    glPushMatrix(); glTranslatef(0,2.5,0); draw_cone(0.22,0.7+0.45*flame,12); glPopMatrix()
    glDisable(GL_BLEND)
    setup_lighting()

# ── Trajectory ─────────────────────────────────────────────────────────────────
def draw_trajectory():
    px,py,pz=lander_x,lander_y,lander_z
    vx,vy,vz=vel_x,vel_y,vel_z; sf,so=fuel,oxygen
    fwx,fwz=0.0,1.0; rtx,rtz=1.0,0.0
    G=diff_gravity(); DR=diff_drag(); TU=diff_thrust_up()
    TH=diff_thrust_horiz(); FB=diff_fuel_burn(); MX=diff_max_vel()
    ku=key_space_held(); kd=key_dn_held()
    kw=key_w_held(); ks=key_s_held(); ka=key_a_held(); kk=key_d_held()
    pts=[(px,py,pz)]
    for _ in range(500):
        vy+=G; hf=sf>0; ho=so>0
        if ku:
            if hf:   vy+=TU; sf=max(0,sf-FB)
            elif ho: vy+=TU*0.55; so=max(0,so-0.10)
            dx=dz=0.0
            if kw: dx+=fwx; dz+=fwz
            if ks: dx-=fwx; dz-=fwz
            if kk: dx+=rtx; dz+=rtz
            if ka: dx-=rtx; dz-=rtz
            dl=math.sqrt(dx*dx+dz*dz)
            if dl>1e-9:
                dx/=dl; dz/=dl; vx+=dx*(TU*0.60); vz+=dz*(TU*0.60)
        if kd:
            if hf:   vy-=TU*0.45; sf=max(0,sf-FB*0.5)
            elif ho: vy-=TU*0.25; so=max(0,so-0.06)
        if kw: vx+=fwx*TH; vz+=fwz*TH
        if ks: vx-=fwx*TH; vz-=fwz*TH
        if ka: vx-=rtx*TH; vz-=rtz*TH
        if kk: vx+=rtx*TH; vz+=rtz*TH
        wx2,wz2=get_wind(); vx+=wx2; vz+=wz2
        vx*=DR; vz*=DR
        vx=max(-MX,min(MX,vx)); vz=max(-MX,min(MX,vz)); vy=max(-MX,min(MX,vy))
        px+=vx; py+=vy; pz+=vz
        gy=terrain_height(px,pz)
        if py<=gy+0.5: py=gy+0.5; pts.append((px,py,pz)); break
        pts.append((px,py,pz))
    if len(pts)<2: return
    spd=math.sqrt(vx**2+vy**2+vz**2)*60; lv=get_land_vel_max()
    lr,lg,lb=(0.2,1.0,0.3) if spd<=lv else (1.0,0.85,0.0) if spd<=lv*1.5 else (1.0,0.2,0.1)
    disable_lighting()
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
    glBegin(GL_LINE_STRIP)
    for idx,(tx2,ty2,tz2) in enumerate(pts):
        fade=1.0-(idx/len(pts))*0.75
        glColor4f(lr*fade,lg*fade,lb*fade,fade*0.8)
        glVertex3f(tx2,ty2,tz2)
    glEnd()
    glDisable(GL_BLEND)
    ix,iy,iz=pts[-1]
    glColor3f(lr,lg,lb)
    glBegin(GL_LINES)
    glVertex3f(ix-2,iy+0.15,iz); glVertex3f(ix+2,iy+0.15,iz)
    glVertex3f(ix,iy+0.15,iz-2); glVertex3f(ix,iy+0.15,iz+2)
    glEnd()
    glPointSize(8.0); glBegin(GL_POINTS); glVertex3f(ix,iy+0.15,iz); glEnd()
    glPointSize(1.0)
    setup_lighting()

# ── Minimap ───────────────────────────────────────────────────────────────────
def draw_minimap():
    MW=200; MH=200; MX_vp=WIN_W-MW-10; MY_vp=10
    old_depth=glIsEnabled(GL_DEPTH_TEST)
    glViewport(MX_vp,MY_vp,MW,MH)
    half=float(WORLD_HALF+10)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    glScalef(1.0/half,1.0/half,1.0)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glDisable(GL_DEPTH_TEST); disable_lighting()
    # Background
    glColor3f(0.04,0.04,0.10)
    glBegin(GL_QUADS)
    glVertex2f(-half,-half); glVertex2f(half,-half)
    glVertex2f(half,half);   glVertex2f(-half,half); glEnd()
    glColor3f(0.3,0.3,0.5)
    glBegin(GL_LINE_LOOP)
    glVertex2f(-half,-half); glVertex2f(half,-half)
    glVertex2f(half,half);   glVertex2f(-half,half); glEnd()
    danger=min(1.0,(level-1)/9.0); ring_r=max(get_target_radius(),8.0)
    glColor3f(1.0,1.0-danger*0.8,0.0)
    glBegin(GL_LINE_LOOP)
    for s in range(32):
        a=2*math.pi*s/32
        glVertex2f(target_x+ring_r*math.cos(a),target_z+ring_r*math.sin(a))
    glEnd()
    glColor3f(1.0,0.5,0.0); glPointSize(10.0)
    glBegin(GL_POINTS); glVertex2f(target_x,target_z); glEnd()
    glColor3f(0.6,0.6,0.0)
    glBegin(GL_LINES)
    glVertex2f(lander_x,lander_z); glVertex2f(target_x,target_z); glEnd()
    hr=math.radians(rocket_heading); arrow_len=max(18.0,half*0.06)
    glColor3f(0.0,1.0,1.0)
    glBegin(GL_LINES)
    glVertex2f(lander_x,lander_z)
    glVertex2f(lander_x+math.sin(hr)*arrow_len,lander_z+math.cos(hr)*arrow_len); glEnd()
    glColor3f(1.0,1.0,0.0); glPointSize(10.0)
    glBegin(GL_POINTS); glVertex2f(lander_x,lander_z); glEnd()
    glPointSize(1.0)
    glEnable(GL_DEPTH_TEST) if old_depth else glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glViewport(0,0,WIN_W,WIN_H)
    setup_lighting()

# ── HUD ───────────────────────────────────────────────────────────────────────
def draw_panel_bg(x0,y0,x1,y1,alpha=0.65):
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0.0,0.0,0.0,alpha)
    glBegin(GL_QUADS)
    glVertex2f(x0,y0); glVertex2f(x1,y0)
    glVertex2f(x1,y1); glVertex2f(x0,y1); glEnd()
    glColor4f(0.25,0.25,0.45,0.9)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x0,y0); glVertex2f(x1,y0)
    glVertex2f(x1,y1); glVertex2f(x0,y1); glEnd()
    glDisable(GL_BLEND)

def draw_bar(x, y, w, h, pct, col_fg, col_bg=(0.08,0.08,0.08)):
    glColor3f(*col_bg)
    glBegin(GL_QUADS)
    glVertex2f(x,y); glVertex2f(x+w,y); glVertex2f(x+w,y+h); glVertex2f(x,y+h); glEnd()
    glColor3f(*col_fg)
    fw=w*max(0.0,min(1.0,pct))
    glBegin(GL_QUADS)
    glVertex2f(x,y); glVertex2f(x+fw,y); glVertex2f(x+fw,y+h); glVertex2f(x,y+h); glEnd()

def draw_hud():
    speed=math.sqrt(vel_x**2+vel_y**2+vel_z**2)*60
    dtgt=math.sqrt((lander_x-target_x)**2+(lander_z-target_z)**2)
    alt=max(0.0,lander_y-terrain_height(lander_x,lander_z))
    lv=get_land_vel_max(); rad=get_target_radius()
    on_oxy=(fuel<=0 and oxygen>0); both_empty=(fuel<=0 and oxygen<=0)
    blink=abs(math.sin(animation_time*10.0))

    _ortho_push(); glDisable(GL_DEPTH_TEST); disable_lighting()

    # Left panel
    draw_panel_bg(10,WIN_H-250,430,WIN_H-10)
    fc=(1.0,0.55+0.35*blink,0.0) if on_oxy else (1.0,0.1+0.7*blink,0.1) if fuel<10 else (1.0,0.6,0.0) if fuel<30 else (0.2,0.9,0.2)
    draw_text(20,WIN_H-30,f"FUEL:   {fuel:05.1f}%",*fc)
    bcol=(0.9,0.5,0.0) if on_oxy else (1.0,0.1,0.1) if fuel<10 else (1.0,0.6,0.0) if fuel<30 else (0.2,0.9,0.2)
    draw_bar(115,WIN_H-45,300,14,fuel/100.0,bcol)

    oc=(1.0,0.1+0.7*blink,0.1) if oxygen<10 else (1.0,0.75,0.0) if oxygen<30 else (0.2,0.6,1.0)
    draw_text(20,WIN_H-62,f"OXYGEN: {oxygen:05.1f}%",*oc)
    ocol=(1.0,0.1,0.1) if oxygen<10 else (1.0,0.75,0.0) if oxygen<30 else (0.2,0.6,1.0)
    draw_bar(115,WIN_H-77,300,14,oxygen/100.0,ocol)

    if both_empty:
        draw_text(20,WIN_H-97,"!! NO PROPELLANT - FREE FALL !!",1.0,blink*0.2,blink*0.2)
    elif on_oxy:
        draw_text(20,WIN_H-97,"!! OXYGEN BACKUP ACTIVE !!",1.0,0.5+0.4*blink,0.0)
    elif oxygen<15:
        draw_text(20,WIN_H-97,"!! OXYGEN CRITICAL !!",1.0,blink*0.3,blink*0.3)
    elif fuel<15:
        draw_text(20,WIN_H-97,"!! FUEL LOW !!",1.0,0.5+0.4*blink,0.0)
    else:
        draw_text(20,WIN_H-97,"  ",0,0,0)

    c2=(0.0,1.0,0.0) if speed<=lv else (1.0,0.3,0.1)
    draw_text(20,WIN_H-117,f"SPEED:  {speed:05.2f} u/s  (safe <= {lv:.1f})",*c2)
    # Speed bar
    draw_bar(115,WIN_H-132,300,10,min(speed/(lv*3),1.0),(1.0,0.2,0.1) if speed>lv else (0.0,1.0,0.0))

    ac=(0.2,1.0,0.8) if alt>5 else (1.0,0.6,0.0) if alt>2 else (1.0,0.2,0.1)
    draw_text(20,WIN_H-150,f"ALT:    {alt:05.1f} m",*ac)
    draw_text(20,WIN_H-168,f"VEL  X:{vel_x:+.3f}  Y:{vel_y:+.3f}  Z:{vel_z:+.3f}",0.6,0.6,0.9)
    dc=(0.0,1.0,0.5) if dtgt<rad*2 else (1.0,1.0,0.3) if dtgt<60 else (0.8,0.8,0.8)
    draw_text(20,WIN_H-186,f"TARGET: {dtgt:05.1f} m   PAD: {rad:.2f}m",*dc)
    draw_text(20,WIN_H-206,"SPACE=Thrust  WASD=Move  ARROWS=Cam  C=Autopilot",0.38,0.38,0.38)
    draw_text(20,WIN_H-222,"R=Retry  Q=Full Reset  ESC=Menu",0.32,0.32,0.32)

    # Active keys indicator
    active=[]
    if key_space_held(): active.append("THRUST(OXY)" if on_oxy else "THRUST")
    if key_dn_held():    active.append("RETRO")
    if key_w_held():     active.append("W")
    if key_s_held():     active.append("S")
    if key_a_held():     active.append("A")
    if key_d_held():     active.append("D")
    if active:
        p=0.5+0.5*math.sin(animation_time*12)
        joined=" | ".join(active)
        draw_panel_bg(WIN_W//2-len(joined)*5-20,WIN_H-55,WIN_W//2+len(joined)*5+20,WIN_H-10,0.5)
        draw_text(WIN_W//2-len(joined)*5,WIN_H-30,joined,1.0,0.5+0.5*p,0.0)

    # Right panel
    draw_panel_bg(WIN_W-240,WIN_H-205,WIN_W-10,WIN_H-10)
    danger=min(1.0,(level-1)/9.0); lc=(1.0,1.0-danger*0.8,0.0)
    draw_text(WIN_W-230,WIN_H-30, f"SCORE:  {score}",1.0,0.9,0.1)
    draw_text(WIN_W-230,WIN_H-55, f"LEVEL:  {level}",*lc)
    draw_text(WIN_W-230,WIN_H-80, f"PAD R:  {rad:.2f} m",*lc)
    draw_text(WIN_W-230,WIN_H-105,f"MAX V:  {lv:.1f} u/s",*lc)
    draw_text(WIN_W-230,WIN_H-130,f"GRAV:   {diff_gravity():.4f}",0.6,0.5,0.8)
    draw_text(WIN_W-230,WIN_H-155,f"WIND:   {get_wind()[0]:.5f}",0.5,0.7,0.9)

    ap_blink=abs(math.sin(animation_time*6.0))
    if autopilot:
        draw_text(WIN_W-230,WIN_H-180,"[C] AUTOPILOT: ON ",0.0,1.0,0.2+0.6*ap_blink)
    else:
        draw_text(WIN_W-230,WIN_H-180,"[C] AUTOPILOT: OFF",0.45,0.45,0.45)

    # New target flash
    elapsed=animation_time-new_target_flash_start
    if elapsed<5.0:
        bf=abs(math.sin(animation_time*7)); fade2=1.0-elapsed/5.0
        draw_panel_bg(WIN_W//2-220,WIN_H//2+50,WIN_W//2+220,WIN_H//2+80,0.55)
        draw_text(WIN_W//2-180,WIN_H//2+58,f"** NEW TARGET! {dtgt:.0f}m AWAY **",bf*fade2,fade2,0.0)

    draw_text(20,50,"ESC:MENU  R:RETRY  Q:FULL RESET",0.38,0.38,0.38)

    # Landing message
    if game_over and landing_msg:
        ok="PERFECT" in landing_msg.upper()
        c3=(0.0,1.0,0.3) if ok else (1.0,0.2,0.1)
        draw_panel_bg(WIN_W//2-360,WIN_H//2-115,WIN_W//2+360,WIN_H//2+75)
        draw_text18(WIN_W//2-len(landing_msg)*6,WIN_H//2+22,landing_msg,*c3)
        draw_text(WIN_W//2-220,WIN_H//2-8,"R: RETRY (keep score)  |  Q: FULL RESET  |  ESC: MENU",0.8,0.8,0.8)
        draw_text(WIN_W//2-130,WIN_H//2-42,f"SCORE: {score}   LEVEL: {level}",1.0,0.85,0.0)

    if not game_started and not game_over:
        draw_panel_bg(WIN_W//2-250,WIN_H//2-55,WIN_W//2+250,WIN_H//2-15,0.5)
        draw_text(WIN_W//2-235,WIN_H//2-30,"HOLD SPACE to lift off  |  WASD + Arrows all combinable",0.9,0.9,0.2)

    glEnable(GL_DEPTH_TEST)
    setup_lighting()
    _ortho_pop()

# ── Physics ───────────────────────────────────────────────────────────────────
def update_physics():
    global lander_x,lander_y,lander_z,vel_x,vel_y,vel_z
    global fuel,oxygen,game_over,landing_msg,lander_tilt_z,lander_tilt_x
    global score,level,rocket_heading,autopilot,screen_shake

    if game_over or not game_started:
        lander_tilt_z*=0.92; lander_tilt_x*=0.92; return

    G=diff_gravity(); DR=diff_drag(); TU=diff_thrust_up()
    TH=diff_thrust_horiz(); FB=diff_fuel_burn(); MX=diff_max_vel()
    fwx,fwz=0.0,1.0; rtx,rtz=1.0,0.0

    vel_y+=G
    hf=fuel>0; ho=oxygen>0; oo=(not hf) and ho
    any_key=(key_space_held() or key_dn_held() or
             key_w_held() or key_s_held() or key_a_held() or key_d_held())

    # Exhaust particles
    if key_space_held() and (hf or ho):
        spawn_exhaust(lander_x, lander_y-0.5, lander_z, count=5, is_oxy=(not hf and ho))
    if key_dn_held() and (hf or ho):
        spawn_exhaust(lander_x, lander_y+2.5, lander_z, count=3, retro=True)

    # ── AUTOPILOT
    if autopilot:
        gy_now=terrain_height(lander_x,lander_z)
        alt_now=lander_y-gy_now
        dx_t=target_x-lander_x; dz_t=target_z-lander_z
        dist_h=math.sqrt(dx_t**2+dz_t**2)
        if dist_h>0.5:
            rocket_heading=(math.degrees(math.atan2(dx_t,dz_t)))%360.0
        if dist_h>1.0:
            push=min(0.9,dist_h*0.012)
            nx_t=dx_t/dist_h; nz_t=dz_t/dist_h
            vel_x+=nx_t*push*TH*6.0; vel_z+=nz_t*push*TH*6.0
        else:
            vel_x*=0.88; vel_z*=0.88
        safe_descent=-min(0.28,0.06*math.sqrt(max(alt_now,0.1)))
        v_err=safe_descent-vel_y
        ap_thrust=max(0.0,min(v_err*6.0,TU))
        if alt_now>0.6:
            if hf:
                vel_y+=ap_thrust; fuel=max(0,fuel-FB*(ap_thrust/max(TU,1e-9))*1.4)
                spawn_exhaust(lander_x,lander_y-0.5,lander_z,count=3)
            elif ho:
                vel_y+=ap_thrust*0.55; oxygen=max(0,oxygen-0.10*(ap_thrust/max(TU,1e-9))*1.4)
                spawn_exhaust(lander_x,lander_y-0.5,lander_z,count=3,is_oxy=True)
        lander_tilt_z*=0.88; lander_tilt_x*=0.88
        wx2,wz2=get_wind(); vel_x+=wx2; vel_z+=wz2
        vel_x*=DR; vel_z*=DR
        vel_x=max(-MX,min(MX,vel_x)); vel_z=max(-MX,min(MX,vel_z)); vel_y=max(-MX,min(MX,vel_y))
        lander_x+=vel_x; lander_y+=vel_y; lander_z+=vel_z
        gy=terrain_height(lander_x,lander_z)
        if fuel<=0 and oxygen<=0 and lander_y>gy+0.5:
            landing_msg=f"OUT OF PROPELLANT! Score:{score}"; game_over=True
            vel_x=vel_y=vel_z=0; move_target(); screen_shake=0.8; return
        if lander_y<=gy+0.5:
            lander_y=gy+0.5
            _handle_landing()
        return

    # Manual controls
    if key_space_held():
        if hf:   vel_y+=TU; fuel=max(0,fuel-FB)
        elif ho: vel_y+=TU*0.55; oxygen=max(0,oxygen-0.10)
        dx=dz=0.0
        if key_w_held(): dx+=fwx; dz+=fwz
        if key_s_held(): dx-=fwx; dz-=fwz
        if key_d_held(): dx+=rtx; dz+=rtz
        if key_a_held(): dx-=rtx; dz-=rtz
        dl=math.sqrt(dx*dx+dz*dz)
        if dl>1e-9:
            dx/=dl; dz/=dl; vel_x+=dx*(TU*0.60); vel_z+=dz*(TU*0.60)
    if key_dn_held():
        if hf:   vel_y-=TU*0.45; fuel=max(0,fuel-FB*0.5)
        elif ho: vel_y-=TU*0.25; oxygen=max(0,oxygen-0.06)

    any_strafe=False
    for pressed,ddx,ddz,ta,td in [
        (key_w_held(),+fwx,+fwz,'x',-1),
        (key_s_held(),-fwx,-fwz,'x',+1),
        (key_d_held(),+rtx,+rtz,'z',-1),
        (key_a_held(),-rtx,-rtz,'z',+1)]:
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
        vel_x=vel_y=vel_z=0; move_target(); screen_shake=0.9; return
    if lander_y<=gy+0.5:
        lander_y=gy+0.5; _handle_landing()

def _handle_landing():
    global game_over,landing_msg,score,level,screen_shake,vel_x,vel_y,vel_z
    speed=math.sqrt(vel_x**2+vel_y**2+vel_z**2)*60
    lv=get_land_vel_max(); rad=get_target_radius()
    dist_hit=math.sqrt((lander_x-target_x)**2+(lander_z-target_z)**2)
    on_target=(dist_hit<=rad)
    spawn_impact(lander_x,lander_y,lander_z,count=35)
    if on_target and speed<=lv:
        prec=max(0.0,1.0-dist_hit/rad); mult=1.0+prec
        pts=int(max(1,int(10*level))*mult); score+=pts; level+=1
        landing_msg=f"PERFECT! +{pts}pts (x{mult:.1f}) Speed:{speed:.1f} -> LEVEL {level}!"
        screen_shake=0.4
    elif on_target:
        landing_msg=f"TOO FAST! Speed:{speed:.1f} (need<={lv:.1f}) Score:{score}"
        screen_shake=0.8
    else:
        landing_msg=f"CRASHED! {dist_hit:.1f}m from target. Score:{score}"
        screen_shake=1.0
    move_target(); game_over=True
    vel_x=vel_y=vel_z=0

# ── Reset ─────────────────────────────────────────────────────────────────────
def reset_game():
    global lander_x,lander_y,lander_z,vel_x,vel_y,vel_z,fuel,oxygen
    global game_started,game_over,landing_msg,gp_cam_pitch
    global lander_tilt_z,lander_tilt_x,rocket_heading,gp_cam_yaw,gp_cam_dist
    global autopilot,screen_shake,particles
    key_last_seen.clear(); particles.clear()
    lander_x=lander_z=0.0; lander_y=terrain_height(0,0)+75.0
    vel_x=vel_y=vel_z=0.0; fuel=oxygen=100.0
    game_started=game_over=False; landing_msg=""
    gp_cam_pitch=22.0; gp_cam_yaw=0.0; gp_cam_dist=45.0
    lander_tilt_z=lander_tilt_x=rocket_heading=0.0
    autopilot=False; screen_shake=0.0

def full_reset():
    global score,level
    score=0; level=1; move_target(); reset_game()

# ── Display ───────────────────────────────────────────────────────────────────
def show_screen():
    glClearColor(0.04,0.04,0.08,1.0)
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)

    if current_state in ["MENU","OPTIONS"]:
        disable_lighting()
        draw_interactive_scene()
        _ortho_push(); glDisable(GL_DEPTH_TEST)
        # Title
        draw_text18(WIN_W//2-130,WIN_H-80,"LUNAR DESCENT",0.8,0.8,1.0)
        active=main_menu if current_state=="MENU" else options_menu
        for i,opt in enumerate(active): draw_button(WIN_W//2,500-(i*90),opt,i)
        glEnable(GL_DEPTH_TEST); _ortho_pop()

    elif current_state=="TUTORIAL":
        disable_lighting()
        draw_interactive_scene()
        _ortho_push(); glDisable(GL_DEPTH_TEST)
        draw_panel_bg(40,60,WIN_W-40,WIN_H-40,0.80)
        draw_text18(60,WIN_H-70,"LUNAR DESCENT TUTORIAL   (W/S or UP/DOWN to scroll,  ESC = back)",0.7,0.7,0.9)
        y_pos=WIN_H-110; max_lines=28
        for i in range(tutorial_scroll, min(tutorial_scroll+max_lines, len(tutorial_text))):
            line=tutorial_text[i]
            if line.isupper() and len(line)<42 and line:
                draw_text(70,y_pos,line,1.0,1.0,0.3)
            elif line.startswith(tuple("0123456789")):
                draw_text(70,y_pos,line,0.7,1.0,0.7)
            else:
                draw_text(70,y_pos,line,0.87,0.87,0.87)
            y_pos-=22
        scroll_pct=int(100*tutorial_scroll/max(1,len(tutorial_text)-max_lines))
        draw_text(WIN_W-80,50,f"{scroll_pct}%",0.6,0.6,0.6)
        glEnable(GL_DEPTH_TEST); _ortho_pop()

    elif current_state=="ROCKET_LIST":
        disable_lighting()
        draw_interactive_scene()
        _ortho_push(); glDisable(GL_DEPTH_TEST)
        draw_panel_bg(WIN_W//2-200,120,WIN_W//2+200,680,0.7)
        draw_text18(WIN_W//2-120,640,"SELECT SPACECRAFT",1,1,1)
        for i in range(3): draw_button(WIN_W//2,500-(i*100),rocket_list[i],i)
        draw_button(WIN_W//2,200,"START MISSION",3)
        draw_button(150,50," BACK ",99)
        if show_alert:
            draw_text(WIN_W//2-130,350,alert_message,1,0.2,0.2)
        glEnable(GL_DEPTH_TEST); _ortho_pop()

    elif current_state=="ROCKET_VIEWER":
        setup_lighting()
        set_perspective(45,WIN_W/WIN_H,0.1,100.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        glTranslatef(0,0,-25*zoom_level)
        glRotatef(cam_rx,1,0,0); glRotatef(cam_ry,0,1,0)
        glTranslatef(0,-1.5,0)
        if   selected_rocket_index==0: draw_jak_hound()
        elif selected_rocket_index==1: draw_eva_nation()
        elif selected_rocket_index==2: draw_jf17_thunder()
        disable_lighting()
        _ortho_push(); glDisable(GL_DEPTH_TEST)
        draw_panel_bg(10,WIN_H-100,600,WIN_H-10,0.65)
        draw_text18(20,WIN_H-35,f"INSPECTING: {rocket_list[selected_rocket_index]}",1,1,0)
        sel=(selected_rocket_for_game==selected_rocket_index)
        if sel: draw_text(20,WIN_H-65,"[SELECTED]  F: reselect",0,1,0)
        else:   draw_text(20,WIN_H-65,"Press F to select this rocket",0.7,0.7,0.7)
        draw_text(20,WIN_H-85,"ARROWS: Rotate  |  N: Zoom In  |  M: Zoom Out  |  ESC: Back",0.5,0.5,0.5)
        draw_button(150,50," BACK ",99)
        glEnable(GL_DEPTH_TEST); _ortho_pop()

    elif current_state=="GAMEPLAY":
        setup_lighting()
        set_perspective(58,WIN_W/WIN_H,1.0,1800.0)

        # Screen shake
        sx = shake_x * screen_shake * 0.8
        sy2 = shake_y * screen_shake * 0.8

        hr=math.radians(gp_cam_yaw); pr=math.radians(gp_cam_pitch)
        ecx=lander_x - math.sin(hr)*gp_cam_dist*math.cos(pr) + sx
        ecy=lander_y + gp_cam_dist*math.sin(pr) + sy2
        ecz=lander_z - math.cos(hr)*gp_cam_dist*math.cos(pr)
        set_camera(ecx,ecy,ecz, lander_x,lander_y,lander_z)

        draw_space_background()
        setup_lighting()
        draw_terrain()
        disable_lighting()
        draw_target()
        draw_heading_indicator()
        draw_new_target_arrow()
        if not game_over: draw_trajectory()

        setup_lighting()
        glPushMatrix()
        glTranslatef(lander_x,lander_y,lander_z)
        glRotatef(lander_tilt_z,0,0,1)
        glRotatef(lander_tilt_x,1,0,0)
        glScalef(1.5,1.5,1.5)
        draw_selected_rocket()
        disable_lighting()
        draw_thrust_flame()
        draw_retro_flame()
        glPopMatrix()

        draw_particles()
        draw_hud()
        draw_minimap()

    glutSwapBuffers()

# ── Input ─────────────────────────────────────────────────────────────────────
def keyboard_listener(key, x, y):
    global current_state,selected_option,zoom_level
    global selected_rocket_index,selected_rocket_for_game
    global rocket_selected,show_alert,alert_message,tutorial_scroll

    k=key.lower() if isinstance(key,bytes) else key

    if k==b'\x1b':
        key_last_seen.clear()
        if current_state=="GAMEPLAY":        current_state="MENU";        reset_game()
        elif current_state=="OPTIONS":       current_state="MENU";        selected_option=1
        elif current_state=="ROCKET_LIST":   current_state="OPTIONS";     selected_option=1; show_alert=False
        elif current_state=="ROCKET_VIEWER": current_state="ROCKET_LIST"; selected_option=selected_rocket_index
        elif current_state=="TUTORIAL":      current_state="OPTIONS";     selected_option=0; tutorial_scroll=0
        glutPostRedisplay(); return

    if current_state=="GAMEPLAY":
        if k in (b'w',b's',b'a',b'd'): _key_press(k)
        if k==b' ': _key_press(b'\x00sp')
        if k==b'r': reset_game()
        if k==b'q': full_reset()
        if k==b'c':
            global autopilot; autopilot=not autopilot
        glutPostRedisplay(); return

    if current_state=="TUTORIAL":
        if k==b'w': tutorial_scroll=max(0,tutorial_scroll-3)
        if k==b's': tutorial_scroll=min(len(tutorial_text)-1,tutorial_scroll+3)
        glutPostRedisplay(); return

    if current_state in ["MENU","OPTIONS","ROCKET_LIST"]:
        menu_items=(main_menu if current_state=="MENU"
                    else options_menu if current_state=="OPTIONS"
                    else rocket_list)
        max_opt=len(menu_items)-1
        if selected_option<0 or selected_option>max_opt: selected_option=0
        if k==b'\r':
            if current_state=="MENU":
                if selected_option==0: current_state="ROCKET_LIST"; selected_option=selected_rocket_for_game
                elif selected_option==1: current_state="OPTIONS"; selected_option=-1
                elif selected_option==2: _os._exit(0)
            elif current_state=="OPTIONS":
                if selected_option==0: current_state="TUTORIAL"; selected_option=-1; tutorial_scroll=0
                elif selected_option==1: current_state="ROCKET_LIST"; selected_option=-1
                elif selected_option==2: current_state="MENU"; selected_option=1
            elif current_state=="ROCKET_LIST":
                if 0<=selected_option<3: selected_rocket_index=selected_option; current_state="ROCKET_VIEWER"
                elif selected_option==3:
                    if not rocket_selected: show_alert=True; alert_message="Select a spacecraft first!"
                    else: full_reset(); current_state="GAMEPLAY"

    if current_state=="ROCKET_VIEWER":
        if k==b'n': zoom_level=max(0.2,zoom_level-0.1)
        elif k==b'm': zoom_level=min(3.0,zoom_level+0.1)
        elif k==b'f': selected_rocket_for_game=selected_rocket_index; rocket_selected=True
    glutPostRedisplay()

def keyboard_up_listener(key, x, y):
    """Remove key from held set on key-up for crisp response."""
    k=key.lower() if isinstance(key,bytes) else key
    if k==b' ': key_last_seen.pop(b'\x00sp',None)
    elif k in (b'w',b's',b'a',b'd'): key_last_seen.pop(k,None)

def special_key_listener(key, x, y):
    global cam_rx,cam_ry,selected_option,gp_cam_pitch,gp_cam_yaw,gp_cam_dist,tutorial_scroll

    if current_state=="GAMEPLAY":
        if   key==GLUT_KEY_LEFT:      gp_cam_yaw=(gp_cam_yaw-4.0)%360.0; _key_press(b'\x00lt')
        elif key==GLUT_KEY_RIGHT:     gp_cam_yaw=(gp_cam_yaw+4.0)%360.0; _key_press(b'\x00rt')
        elif key==GLUT_KEY_UP:        gp_cam_pitch=min(80.0,gp_cam_pitch+2.5)
        elif key==GLUT_KEY_DOWN:      gp_cam_pitch=max(5.0,gp_cam_pitch-2.5)
        elif key==GLUT_KEY_PAGE_UP:   gp_cam_dist=max(18.0,gp_cam_dist-2.0)
        elif key==GLUT_KEY_PAGE_DOWN: gp_cam_dist=min(90.0,gp_cam_dist+2.0)
        elif key==GLUT_KEY_DOWN:      _key_press(b'\x00dn')
    elif current_state=="ROCKET_VIEWER":
        if   key==GLUT_KEY_LEFT:  cam_ry-=5
        elif key==GLUT_KEY_RIGHT: cam_ry+=5
        elif key==GLUT_KEY_UP:    cam_rx-=5
        elif key==GLUT_KEY_DOWN:  cam_rx+=5
    elif current_state=="TUTORIAL":
        if   key==GLUT_KEY_UP:   tutorial_scroll=max(0,tutorial_scroll-3)
        elif key==GLUT_KEY_DOWN: tutorial_scroll=min(len(tutorial_text)-1,tutorial_scroll+3)
    elif current_state in ["MENU","OPTIONS","ROCKET_LIST"]:
        menu_items=(main_menu if current_state=="MENU"
                    else options_menu if current_state=="OPTIONS"
                    else rocket_list)
        max_opt=len(menu_items)-1
        if selected_option<0: selected_option=0
        if   key==GLUT_KEY_UP:   selected_option=max(0,selected_option-1)
        elif key==GLUT_KEY_DOWN: selected_option=min(max_opt,selected_option+1)
    glutPostRedisplay()

def special_key_up_listener(key, x, y):
    if current_state=="GAMEPLAY":
        if key==GLUT_KEY_DOWN: key_last_seen.pop(b'\x00dn',None)

def mouse_listener(button,state,x,y):
    global current_state,selected_option,selected_rocket_index
    global last_click_x,last_click_y,rocket_selected,show_alert,alert_message,tutorial_scroll

    if button==GLUT_LEFT_BUTTON and state==GLUT_DOWN:
        last_click_x,last_click_y=x,y; ly=WIN_H-y
        cx=WIN_W//2
        if current_state=="TUTORIAL":
            if x<=250 and ly<=100: current_state="OPTIONS"; selected_option=0; tutorial_scroll=0
        elif current_state=="ROCKET_LIST":
            for i in range(3):
                if cx-100<=x<=cx+100 and (500-(i*100)-10)<=ly<=(500-(i*100)+25):
                    selected_rocket_index=i; current_state="ROCKET_VIEWER"
            if cx-100<=x<=cx+100 and 190<=ly<=225:
                if not rocket_selected: show_alert=True; alert_message="Select a spacecraft first!"
                else: full_reset(); current_state="GAMEPLAY"
            if x<=250 and ly<=100: current_state="OPTIONS"; selected_option=1
        elif current_state=="ROCKET_VIEWER":
            if x<=250 and ly<=100: current_state="ROCKET_LIST"
        else:
            active=main_menu if current_state=="MENU" else options_menu
            for i in range(len(active)):
                if cx-100<=x<=cx+100 and (500-(i*90)-10)<=ly<=(500-(i*90)+25):
                    if selected_option==i:
                        if current_state=="MENU":
                            if i==0: current_state="ROCKET_LIST"; selected_option=selected_rocket_for_game
                            elif i==1: current_state="OPTIONS"; selected_option=-1
                            elif i==2: _os._exit(0)
                        elif current_state=="OPTIONS":
                            if i==0: current_state="TUTORIAL"; selected_option=-1; tutorial_scroll=0
                            elif i==1: current_state="ROCKET_LIST"; selected_option=-1
                            elif i==2: current_state="MENU"; selected_option=1
                    else: selected_option=i
    glutPostRedisplay()

# ── Idle / Timer ──────────────────────────────────────────────────────────────
def idle():
    global animation_time,planet_rotation_y,frame_count,dt,last_frame_time
    global screen_shake,shake_x,shake_y

    now=time.time()
    dt=min(now-last_frame_time, 0.05)   # cap at 50ms to avoid spiral-of-death
    last_frame_time=now

    frame_count+=1
    animation_time+=dt
    planet_rotation_y+=dt*1.5

    # Screen shake decay
    if screen_shake>0.001:
        screen_shake*=0.88
        shake_x=random.uniform(-1,1)
        shake_y=random.uniform(-1,1)
    else:
        screen_shake=0.0; shake_x=shake_y=0.0

    if current_state=="GAMEPLAY":
        update_physics()
        update_particles()

    glutPostRedisplay()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global last_frame_time
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH|GLUT_MULTISAMPLE)
    glutInitWindowSize(WIN_W,WIN_H)
    glutInitWindowPosition(100,50)
    glutCreateWindow(b"Lunar Descent")
    glEnable(GL_MULTISAMPLE)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
    glEnable(GL_LINE_SMOOTH)
    glEnable(GL_POINT_SMOOTH)
    glLineWidth(1.5)

    glutDisplayFunc(show_screen)
    glutKeyboardFunc(keyboard_listener)
    glutKeyboardUpFunc(keyboard_up_listener)
    glutSpecialFunc(special_key_listener)
    glutSpecialUpFunc(special_key_up_listener)
    glutMouseFunc(mouse_listener)
    glutIdleFunc(idle)

    last_frame_time=time.time()
    move_target()
    reset_game()
    glutMainLoop()

if __name__=="__main__":
    main()
