from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, random, os as _os


WIN_W, WIN_H = 1000, 800

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

cam_x, cam_y = 15.0, 0.0
zoom_level   = 1.0

main_menu    = ["START GAME", "OPTIONS", "QUIT"]
options_menu = ["TUTORIAL", "CHECK ROCKET", "BACK"]
rocket_list  = ["JakHound F-22 Raptor", "EvaNation F-15 Eagle",
                "TasroFighter JF17 Thunder", "START MISSION"]

lander_x = 0.0; lander_y = 80.0; lander_z = 0.0
vel_x = vel_y = vel_z = 0.0
fuel = 100.0; oxygen = 100.0
game_started = False
game_over    = False
landing_msg  = ""

lander_tilt_z = lander_tilt_x = lander_rot_y = rocket_heading = 0.0

key_w = key_s = key_a = key_d = False
key_up = key_down = False

gp_cam_pitch = 22.0
gp_cam_dist  = 45.0

score = 0
level = 1
target_x = target_z = 0.0
target_surface_y     = 0.0
new_target_flash_start = -999.0

MAX_TILT      = 22.0
TILT_SPEED    = 1.6
TILT_RECOVERY = 2.8
FUEL_REGEN_RATE = 0.28

# ── Terrain world ──────────────────────────────────────────────────────────
WORLD_HALF   = 320          # ±320 → 640 wide world
TERRAIN_DIVS = 110          # grid resolution (display list compiled once)

_terrain_dl   = None        # OpenGL display list handle
_mountains    = []
_craters      = []
terrain_verts = []          # (x,y,z) per grid node — used for height lookup

# ── Difficulty ─────────────────────────────────────────────────────────────
def diff_gravity():       return max(-0.016, -0.007 - (level-1)*0.00075)
def diff_drag():          return max(0.945,  0.980  - (level-1)*0.0038)
def diff_thrust_up():     return 0.020
def diff_thrust_horiz():  return 0.007
def diff_max_vel_horiz(): return 0.40
def diff_max_vel_up():    return 0.45
def diff_fuel_burn():     return max(0.09,   0.12   + (level-1)*0.004)
def get_land_vel_max():   return max(4.5,    22.0   - (level-1)*1.8)
def get_target_radius():  return max(0.8,    6.5    - (level-1)*0.60)

def get_wind():
    if level < 4: return 0.0, 0.0
    s = (level-3)*0.00028
    a = math.radians(animation_time*4.0)
    return math.cos(a)*s, math.sin(a)*s

# ═══════════════════════════════════════════════════════════════════════════
#  TERRAIN  — heightmap built once, baked into a GL display list
# ═══════════════════════════════════════════════════════════════════════════
def terrain_height(wx, wz):
    """Analytical height query — used for physics & target placement."""
    y = 0.0
    for (cx,cz,rad,peak) in _mountains:
        d = math.sqrt((wx-cx)**2 + (wz-cz)**2)
        if d < rad:
            t = 1.0 - d/rad
            y += peak * t*t*(3.0 - 2.0*t)          # smoothstep
    for (cx,cz,rad,depth) in _craters:
        d = math.sqrt((wx-cx)**2 + (wz-cz)**2)
        if d < rad:
            t = d/rad
            bowl = -depth*(1.0 - t*t)
            rim  =  depth*0.42*math.exp(-((t-0.86)/0.07)**2)
            y   += bowl + rim
    return y

def _build_terrain_display_list():
    """Bake terrain into a GL display list so draw cost is near-zero."""
    global _terrain_dl, terrain_verts

    step  = (WORLD_HALF*2) / TERRAIN_DIVS
    cols  = TERRAIN_DIVS + 1

    # Build vertex grid
    terrain_verts = []
    for row in range(cols):
        for col in range(cols):
            wx = -WORLD_HALF + col*step
            wz = -WORLD_HALF + row*step
            terrain_verts.append((wx, terrain_height(wx,wz), wz))

    # Delete old list
    if _terrain_dl is not None:
        glDeleteLists(_terrain_dl, 1)

    dl = glGenLists(1)
    glNewList(dl, GL_COMPILE)
    glBegin(GL_TRIANGLES)
    for row in range(TERRAIN_DIVS):
        for col in range(TERRAIN_DIVS):
            i00 = row*cols + col
            i10 = i00 + 1
            i01 = i00 + cols
            i11 = i01 + 1

            def emit(ia, ib, ic):
                va=terrain_verts[ia]; vb=terrain_verts[ib]; vc=terrain_verts[ic]
                # Face normal
                ux,uy,uz = vb[0]-va[0], vb[1]-va[1], vb[2]-va[2]
                vx2,vy2,vz2 = vc[0]-va[0], vc[1]-va[1], vc[2]-va[2]
                nx = uy*vz2 - uz*vy2
                ny = uz*vx2 - ux*vz2
                nz2= ux*vy2 - uy*vx2
                ln = math.sqrt(nx*nx+ny*ny+nz2*nz2)
                if ln>1e-9: nx/=ln; ny/=ln; nz2/=ln
                glNormal3f(nx,ny,nz2)
                for v in (va,vb,vc):
                    avg_y = v[1]
                    t = max(0.0, min(1.0, (avg_y+18)/62.0))
                    base = 0.18 + t*0.36
                    # Slight colour variation per vertex
                    glColor3f(base*0.96, base, base*1.06)
                    glVertex3fv(v)

            emit(i00, i10, i01)
            emit(i10, i11, i01)
    glEnd()
    glEndList()
    
    _terrain_dl = dl

def generate_terrain():
    """Rebuild mountains/craters for current level, then bake display list."""
    global _mountains, _craters
    rng = random.Random(level*31 + 7)

    # ── Mountains  (bigger, more dramatic) ───────────────────────────────
    _mountains = []
    n_mt = 22 + level*2
    for _ in range(n_mt):
        cx  = rng.uniform(-WORLD_HALF+20, WORLD_HALF-20)
        cz  = rng.uniform(-WORLD_HALF+20, WORLD_HALF-20)
        rad = rng.uniform(28, 85)
        pk  = rng.uniform(18, 55)
        _mountains.append((cx, cz, rad, pk))

    # Extra towering peaks
    for _ in range(6+level):
        cx  = rng.uniform(-WORLD_HALF+40, WORLD_HALF-40)
        cz  = rng.uniform(-WORLD_HALF+40, WORLD_HALF-40)
        rad = rng.uniform(20, 45)
        pk  = rng.uniform(55, 90)
        _mountains.append((cx, cz, rad, pk))

    # ── Craters (wider, deeper) ───────────────────────────────────────────
    _craters = []
    n_cr = 30 + level*2
    for _ in range(n_cr):
        cx  = rng.uniform(-WORLD_HALF+10, WORLD_HALF-10)
        cz  = rng.uniform(-WORLD_HALF+10, WORLD_HALF-10)
        rad = rng.uniform(8, 42)
        dep = rng.uniform(5, 20)
        _craters.append((cx, cz, rad, dep))

    # A few mega craters
    for _ in range(4):
        cx  = rng.uniform(-WORLD_HALF+60, WORLD_HALF-60)
        cz  = rng.uniform(-WORLD_HALF+60, WORLD_HALF-60)
        rad = rng.uniform(50, 90)
        dep = rng.uniform(18, 32)
        _craters.append((cx, cz, rad, dep))

    _build_terrain_display_list()

def move_target():
    """Pick a new target guaranteed to be on the FAR side of the world."""
    global target_x, target_z, target_surface_y, new_target_flash_start
    rng = random.Random(level*17 + score*3 + int(animation_time*100))
    spread = min(WORLD_HALF-30, 80 + level*9)   # can reach very far

    for _ in range(800):
        angle = rng.uniform(0, 2*math.pi)
        dist  = rng.uniform(max(80, spread*0.55), spread)
        tx = math.cos(angle)*dist
        tz = math.sin(angle)*dist
        if abs(tx) < WORLD_HALF-15 and abs(tz) < WORLD_HALF-15:
            target_x, target_z = tx, tz
            break

    target_surface_y       = terrain_height(target_x, target_z)
    new_target_flash_start = animation_time
    generate_terrain()      # bake new display list

# ═══════════════════════════════════════════════════════════════════════════
#  STARS
# ═══════════════════════════════════════════════════════════════════════════
star_data = []
for _ in range(700):
    _tx,_ty = random.uniform(-100,100), random.uniform(-60,60)
    star_data.append([_tx,_ty,random.uniform(-150,-20),random.uniform(0.5,0.9),_tx,_ty])

# ═══════════════════════════════════════════════════════════════════════════
#  DRAW HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def draw_text(x,y,text,r,g,b,font=GLUT_BITMAP_9_BY_15):
    glColor3f(r,g,b); tx=x
    for ch in text:
        glRasterPos2f(tx,y); glutBitmapCharacter(font,ord(ch)); tx+=9

def draw_button(x,y,text,index):
    global selected_option
    tw=len(text)*10; x0,x1=x-tw/2-20,x+tw/2+20; y0,y1=y-10,y+25
    gl_y=WIN_H-last_click_y
    if x0<=last_click_x<=x1 and y0<=gl_y<=y1: selected_option=index
    sel=(selected_option==index)
    if sel:  draw_text(x-tw/2,y,text,1.0,1.0,1.0); glColor3f(1.0,0.2,0.2); glLineWidth(3.0)
    else:    draw_text(x-tw/2,y,text,0.7,0.1,0.1); glColor3f(0.4,0.0,0.0); glLineWidth(1.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x0,y0); glVertex2f(x1,y0); glVertex2f(x1,y1); glVertex2f(x0,y1)
    glEnd(); glLineWidth(1.0)

def draw_cylinder_new(br,tr,h,sl=28,st=3): gluCylinder(gluNewQuadric(),br,tr,h,sl,st)
def draw_sphere_new(r,sl=28,st=28):        gluSphere(gluNewQuadric(),r,sl,st)
def draw_disk_new(inner,outer,sl=28):      gluCylinder(gluNewQuadric(),outer,inner,0.01,sl,1)
def draw_cone_new(base,h,sl=28):           draw_cylinder_new(base,0.0,h,sl)

# ═══════════════════════════════════════════════════════════════════════════
#  MENU BACKGROUND
# ═══════════════════════════════════════════════════════════════════════════
def draw_interactive_scene():
    glPointSize(3.0); glBegin(GL_POINTS)
    mx=(last_click_x-500)/6.0; my=(400-last_click_y)/6.0
    for i,s in enumerate(star_data):
        blink=0.2+0.6*abs(math.sin(animation_time*5+i))
        glColor3f(blink*s[3],blink*s[3],blink*s[3])
        dx,dy=mx-s[0],my-s[1]; dist=math.sqrt(dx**2+dy**2)
        if dist<15.0: s[0]+=dx*0.05; s[1]+=dy*0.05
        else:         s[0]+=(s[4]-s[0])*0.02; s[1]+=(s[5]-s[1])*0.02
        glVertex3f(s[0],s[1],s[2])
    glEnd()
    glPushMatrix(); glTranslatef(22,-14,-45)
    glRotatef(planet_rotation_y+(last_click_x-500)/40.0,0,1,0)
    glRotatef((last_click_y-400)/40.0,1,0,0)
    q=gluNewQuadric()
    glColor3f(0.8,0.8,0.82); gluSphere(q,16,48,48)
    glPushMatrix(); glRotatef(animation_time*8,1,1,0)
    glColor3f(0.3,0.3,0.32); gluSphere(q,16.1,8,8); glPopMatrix(); glPopMatrix()

# ═══════════════════════════════════════════════════════════════════════════
#  ROCKET MODELS
# ═══════════════════════════════════════════════════════════════════════════
def draw_eva_nation():
    glColor3f(0.95,0.55,0.75); glPushMatrix(); glRotatef(-90,1,0,0); draw_cylinder_new(0.42,0.38,2.2); glPopMatrix()
    glColor3f(0.97,0.97,0.97); glPushMatrix(); glTranslatef(0,0.8,0.42); glScalef(0.28,0.70,0.05); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.85,0.72,0.30)
    for yw in [0.5,0.9,1.30]:
        glPushMatrix(); glTranslatef(0,yw,0.42); glScalef(0.30,0.04,0.06); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.90,0.40,0.65); glPushMatrix(); glTranslatef(0,2.2,0); glRotatef(-90,1,0,0); draw_cone_new(0.38,1.10); glPopMatrix()
    glColor3f(1.0,0.80,0.90); glPushMatrix(); glTranslatef(0,3.20,0); draw_sphere_new(0.08); glPopMatrix()
    glColor3f(0.85,0.45,0.70); glPushMatrix(); glRotatef(90,1,0,0); draw_disk_new(0.0,0.42); glPopMatrix()
    for i,col in enumerate([(0.80,0.35,0.60),(0.90,0.45,0.70),(0.80,0.35,0.60),(0.90,0.45,0.70)]):
        glColor3f(*col); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.38,0.10,0); glScalef(0.55,0.85,0.06); glutSolidCube(1.0); glPopMatrix()
    for nx,ny,nz in [(-0.16,0,0),(0.16,0,0),(0,0,0)]:
        glColor3f(0.60,0.25,0.50); glPushMatrix(); glTranslatef(nx,-0.05,nz)
        glRotatef(90,1,0,0); draw_cylinder_new(0.10,0.08,0.25); glPopMatrix()
    glColor3f(1.0,0.85,0.92)
    for side in [-1,1]:
        glPushMatrix(); glTranslatef(side*0.40,1.10,0); glScalef(0.06,1.20,0.06); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.55,0.15,0.80); glPushMatrix(); glTranslatef(0,0.05,0); glRotatef(90,1,0,0); draw_cylinder_new(0.44,0.44,0.05,48); glPopMatrix()

def draw_jf17_thunder():
    glColor3f(0.55,0.05,0.05); glPushMatrix(); glRotatef(-90,1,0,0); draw_cylinder_new(0.34,0.30,2.0,6); glPopMatrix()
    glColor3f(0.70,0.08,0.08)
    for px,py,pz,sx,sy,sz in [(0,1.50,0.33,0.24,0.30,0.05),(0,0.90,0.33,0.22,0.28,0.05),(0,0.35,0.33,0.22,0.28,0.05)]:
        glPushMatrix(); glTranslatef(px,py,pz); glScalef(sx,sy,sz); glutSolidCube(1.0); glPopMatrix()
    glColor3f(1.0,0.20,0.05)
    for yy in [0.20,0.60,1.00,1.40,1.80]:
        glPushMatrix(); glTranslatef(0,yy,0.31); glScalef(0.30,0.03,0.04); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.65,0.07,0.07); glPushMatrix(); glTranslatef(0,2.0,0); glRotatef(-90,1,0,0); draw_cone_new(0.30,0.90,6); glPopMatrix()
    glColor3f(0.9,0.3,0.3); glPushMatrix(); glTranslatef(0,2.82,0); draw_sphere_new(0.06); glPopMatrix()
    glColor3f(0.45,0.04,0.04); glPushMatrix(); glRotatef(90,1,0,0); draw_disk_new(0.0,0.34,6); glPopMatrix()
    for fx,fy,fz in [(1,0,0),(-1,0,0),(0,0,1),(0,0,-1)]:
        glColor3f(0.50,0.05,0.05); glPushMatrix(); glTranslatef(fx*0.44,0.15,fz*0.44)
        glScalef(0.40 if fx!=0 else 0.06,0.70,0.40 if fz!=0 else 0.06); glutSolidCube(1.0); glPopMatrix()
    for sx in [-1,1]:
        glColor3f(0.40,0.04,0.04); glPushMatrix(); glTranslatef(sx*0.46,0.30,0)
        glRotatef(-90,1,0,0); draw_cylinder_new(0.10,0.08,0.60); glPopMatrix()
    for nx2,nz2 in [(0,0),(-0.18,0),(0.18,0),(0,-0.18),(0,0.18)]:
        glColor3f(0.30,0.03,0.03); glPushMatrix(); glTranslatef(nx2,-0.05,nz2)
        glRotatef(90,1,0,0); draw_cylinder_new(0.075,0.065,0.22); glPopMatrix()
    flame=0.5+0.5*math.sin(animation_time*8.0)
    glColor3f(1.0,0.4+0.3*flame,0.0); glPushMatrix(); glTranslatef(0,-0.05,0)
    glRotatef(90,1,0,0); draw_cone_new(0.15,0.5+0.4*flame,12); glPopMatrix()

def draw_jak_hound():
    glColor3f(0.14,0.14,0.16); glPushMatrix(); glRotatef(-90,1,0,0); draw_cylinder_new(0.32,0.28,2.10,8); glPopMatrix()
    glColor3f(0.85,0.60,0.10); glPushMatrix(); glTranslatef(0,1.65,0); glRotatef(-90,1,0,0); draw_cylinder_new(0.305,0.295,0.22,8); glPopMatrix()
    glColor3f(0.05,0.55,0.95); glPushMatrix(); glTranslatef(0,1.52,0.33); draw_sphere_new(0.09); glPopMatrix()
    glColor3f(0.10,0.70,1.0); glPushMatrix(); glTranslatef(0,1.52,0.30); glRotatef(90,0,1,0); draw_cylinder_new(0.10,0.10,0.02,24); glPopMatrix()
    glColor3f(0.75,0.55,0.08)
    for py in [0.30,0.65,1.00,1.35]:
        glPushMatrix(); glTranslatef(0,py,0.29); glScalef(0.34,0.025,0.04); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.10,0.10,0.12)
    for side in [-1,1]:
        glPushMatrix(); glTranslatef(side*0.18,0.80,0.28); glScalef(0.16,0.55,0.04); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.80,0.58,0.10)
    for side in [-1,1]:
        glPushMatrix(); glTranslatef(side*0.29,1.00,0); glScalef(0.04,1.60,0.04); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.18,0.18,0.20); glPushMatrix(); glTranslatef(0,2.10,0); glRotatef(-90,1,0,0); draw_cone_new(0.28,0.95,8); glPopMatrix()
    glColor3f(0.80,0.60,0.10); glPushMatrix(); glTranslatef(0,2.97,0); draw_sphere_new(0.07); glPopMatrix()
    glColor3f(0.12,0.12,0.14); glPushMatrix(); glRotatef(90,1,0,0); draw_disk_new(0.0,0.32,8); glPopMatrix()
    for i in range(4):
        glColor3f(0.12,0.12,0.14); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.30,0.10,0); glScalef(0.40,0.65,0.05); glutSolidCube(1.0); glPopMatrix()
        glColor3f(0.75,0.55,0.08); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.50,0.10,0); glScalef(0.04,0.65,0.055); glutSolidCube(1.0); glPopMatrix()
    glColor3f(0.20,0.20,0.22); glPushMatrix(); glTranslatef(0,-0.05,0); glRotatef(90,1,0,0); draw_cylinder_new(0.20,0.17,0.28,8); glPopMatrix()
    glColor3f(0.08,0.08,0.10); glPushMatrix(); glTranslatef(0,-0.05,0); glRotatef(90,1,0,0); draw_cylinder_new(0.15,0.12,0.28,8); glPopMatrix()
    glColor3f(0.75,0.55,0.08); glPushMatrix(); glTranslatef(0,-0.02,0); glRotatef(90,1,0,0); draw_cylinder_new(0.21,0.21,0.04,8); glPopMatrix()

def draw_selected_rocket():
    if   selected_rocket_for_game==0: draw_jak_hound()
    elif selected_rocket_for_game==1: draw_eva_nation()
    elif selected_rocket_for_game==2: draw_jf17_thunder()
    else: draw_jak_hound()

# ═══════════════════════════════════════════════════════════════════════════
#  DRAW TERRAIN  — single display list call
# ═══════════════════════════════════════════════════════════════════════════
def draw_terrain():
    if _terrain_dl is None: return
    glCallList(_terrain_dl)

# ═══════════════════════════════════════════════════════════════════════════
#  TARGET
# ═══════════════════════════════════════════════════════════════════════════
def draw_target():
    cx,cz   = target_x, target_z
    sy      = terrain_height(cx,cz)
    radius  = get_target_radius()
    pulse   = 0.5+0.5*math.sin(animation_time*4.0)
    danger  = min(1.0,(level-1)/9.0)
    tr=1.0; tg=1.0-danger*0.8

    for ring_r,lw in [(radius+2.0,3.0),(radius,2.2),(radius*0.5,2.0)]:
        glColor3f(tr,tg*(pulse*0.8+0.2),0.0); glLineWidth(lw)
        glBegin(GL_LINE_LOOP)
        for s in range(64):
            a=2*math.pi*s/64; wx=cx+ring_r*math.cos(a); wz=cz+ring_r*math.sin(a)
            glVertex3f(wx, terrain_height(wx,wz)+0.15, wz)
        glEnd()

    glColor3f(tr,tg,0.0); glLineWidth(2.5)
    glBegin(GL_LINES)
    glVertex3f(cx-(radius+3),sy+0.15,cz); glVertex3f(cx+(radius+3),sy+0.15,cz)
    glVertex3f(cx,sy+0.15,cz-(radius+3)); glVertex3f(cx,sy+0.15,cz+(radius+3))
    glEnd()

    glColor3f(1.0,0.6,0.0); glLineWidth(1.5)
    for tick in range(8):
        a=2*math.pi*tick/8+animation_time*0.8
        glBegin(GL_LINES)
        glVertex3f(cx+radius*0.75*math.cos(a),sy+0.15,cz+radius*0.75*math.sin(a))
        glVertex3f(cx+radius*1.12*math.cos(a),sy+0.15,cz+radius*1.12*math.sin(a))
        glEnd()

    beacon_h=sy+40.0+pulse*6.0
    glColor3f(tr,tg,0.0); glLineWidth(1.5)
    glBegin(GL_LINES); glVertex3f(cx,sy+0.1,cz); glVertex3f(cx,beacon_h,cz); glEnd()
    glPointSize(10.0); glColor3f(1.0,1.0,0.2*pulse)
    glBegin(GL_POINTS); glVertex3f(cx,beacon_h,cz); glEnd()
    glPointSize(1.0); glLineWidth(1.0)

def draw_new_target_arrow():
    elapsed=animation_time-new_target_flash_start
    if elapsed>5.0: return
    fade=1.0-elapsed/5.0; alpha=fade*abs(math.sin(animation_time*8.0))
    dx=target_x-lander_x; dz=target_z-lander_z
    dist=math.sqrt(dx**2+dz**2)
    if dist<0.01: return
    nx=dx/dist; nz=dz/dist
    ax=lander_x+nx*8; az=lander_z+nz*8; ay=lander_y+3.0
    glLineWidth(4.0); glColor3f(alpha,alpha*0.85,0.0)
    glBegin(GL_LINES); glVertex3f(lander_x,ay,lander_z); glVertex3f(ax,ay,az); glEnd()
    glPointSize(13.0); glBegin(GL_POINTS); glVertex3f(ax,ay,az); glEnd()
    glPointSize(1.0); glLineWidth(1.0)

def draw_wind_indicator():
    if level<4: return
    wx,wz=get_wind(); s=math.sqrt(wx**2+wz**2)
    if s<1e-7: return
    nx=wx/s; nz=wz/s; sc=min(s*80000,1.0)
    glColor3f(0.4*sc,0.6*sc,1.0); glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex3f(lander_x,lander_y+5,lander_z)
    glVertex3f(lander_x+nx*4,lander_y+5,lander_z+nz*4); glEnd(); glLineWidth(1.0)

def draw_heading_indicator():
    sy=terrain_height(lander_x,lander_z)
    hr=math.radians(rocket_heading); fx=math.sin(hr)*6; fz=math.cos(hr)*6
    glColor3f(0.0,1.0,1.0); glLineWidth(2.5)
    glBegin(GL_LINES)
    glVertex3f(lander_x,sy+0.35,lander_z)
    glVertex3f(lander_x+fx,terrain_height(lander_x+fx,lander_z+fz)+0.35,lander_z+fz)
    glEnd(); glLineWidth(1.0)

def draw_space_background():
    q=gluNewQuadric(); glPointSize(2.0); glBegin(GL_POINTS)
    random.seed(7)
    for _ in range(500):
        ang=random.uniform(0,2*math.pi); el=random.uniform(-math.pi/2,math.pi/2); d=450.0
        glColor3f(random.uniform(0.6,1.0),random.uniform(0.6,1.0),random.uniform(0.7,1.0))
        glVertex3f(d*math.cos(el)*math.cos(ang),d*math.sin(el),d*math.cos(el)*math.sin(ang))
    glEnd()
    glPushMatrix(); glRotatef(planet_rotation_y*0.1,0,1,0); glTranslatef(400,100,0)
    glColor3f(1.0,0.9,0.3); gluSphere(q,22,24,24); glPopMatrix()
    glPushMatrix(); glRotatef(planet_rotation_y*0.3,0,1,0); glTranslatef(260,40,-130)
    glColor3f(0.1,0.4,0.8); gluSphere(q,12,24,24)
    glColor3f(0.9,0.9,0.9); glPushMatrix(); glRotatef(planet_rotation_y*2,0,1,0)
    gluSphere(q,12.3,8,8); glPopMatrix(); glPopMatrix()
    glPushMatrix(); glRotatef(planet_rotation_y*0.2,0,1,0); glTranslatef(-220,-25,180)
    glColor3f(0.7,0.25,0.1); gluSphere(q,7,20,20); glPopMatrix()

def draw_thrust_flame():
    if not key_up: return
    if fuel<=0 and oxygen<=0: return
    on_oxy=(fuel<=0 and oxygen>0); flame=0.5+0.5*math.sin(animation_time*15.0)
    glColor3f(0.4,0.6+0.3*flame,1.0) if on_oxy else glColor3f(1.0,0.5+0.3*flame,0.0)
    glPushMatrix(); glTranslatef(0,-0.5,0); glRotatef(90,1,0,0)
    draw_cone_new(0.3,1.0+0.6*flame,12); glPopMatrix()

def draw_retro_flame():
    if not key_down or (fuel<=0 and oxygen<=0): return
    flame=0.4+0.4*math.sin(animation_time*15.0)
    glColor3f(0.5,0.8+0.2*flame,1.0); glPushMatrix(); glTranslatef(0,2.5,0)
    glRotatef(-90,1,0,0); draw_cone_new(0.2,0.6+0.4*flame,12); glPopMatrix()

def draw_side_flame():
    flame=0.3+0.3*math.sin(animation_time*18.0)
    glColor3f(0.8,0.4+0.3*flame,0.0); glPushMatrix(); glTranslatef(0,-0.1,0)
    glRotatef(90,1,0,0); draw_cone_new(0.10,0.3+0.2*flame,8); glPopMatrix()

# ── Trajectory (unchanged physics sim, runs fast) ─────────────────────────
def draw_trajectory():
    px,py,pz=lander_x,lander_y,lander_z; vx,vy,vz=vel_x,vel_y,vel_z
    sim_fuel=fuel; sim_oxy=oxygen
    hr=math.radians(rocket_heading)
    fx=math.sin(hr); fz=math.cos(hr); rx=math.cos(hr); rz=-math.sin(hr)
    G=diff_gravity(); DR=diff_drag(); TU=diff_thrust_up(); TH=diff_thrust_horiz()
    FB=diff_fuel_burn(); MXH=diff_max_vel_horiz(); MXV=diff_max_vel_up()
    pts=[(px,py,pz)]
    for _ in range(500):
        vy+=G
        hf=sim_fuel>0; ho=sim_oxy>0; oo=(not hf) and ho
        if key_up:
            if hf:  vy+=TU; sim_fuel=max(0,sim_fuel-FB)
            elif ho: vy+=TU*0.55; sim_oxy=max(0,sim_oxy-0.10)
        if key_down:
            if hf:  vy-=TU*0.45; sim_fuel=max(0,sim_fuel-FB*0.5)
            elif ho: vy-=TU*0.25; sim_oxy=max(0,sim_oxy-0.06)
        for kk,ddx,ddz in [(key_w,fx,fz),(key_s,-fx,-fz),(key_a,-rx,-rz),(key_d,rx,rz)]:
            if kk:
                vx+=ddx*TH; vz+=ddz*TH
                if hf: sim_fuel=max(0,sim_fuel-FB*0.3)
                elif ho: sim_oxy=max(0,sim_oxy-0.04)
        wx2,wz2=get_wind(); vx+=wx2; vz+=wz2
        vx*=DR; vz*=DR
        vx=max(-MXH,min(MXH,vx)); vz=max(-MXH,min(MXH,vz)); vy=max(-MXV,min(MXV,vy))
        px+=vx; py+=vy; pz+=vz
        gy=terrain_height(px,pz)
        if py<=gy+0.5: py=gy+0.5; pts.append((px,py,pz)); break
        pts.append((px,py,pz))
    if len(pts)<2: return
    spd=math.sqrt(vx**2+vy**2+vz**2)*60; lv=get_land_vel_max()
    lr,lg,lb=(0.2,1.0,0.3) if spd<=lv else (1.0,0.85,0.0) if spd<=lv*1.5 else (1.0,0.2,0.1)
    glLineWidth(1.8); glBegin(GL_LINE_STRIP)
    for idx,(tx2,ty2,tz2) in enumerate(pts):
        fade=1.0-(idx/len(pts))*0.7; glColor3f(lr*fade,lg*fade,lb*fade); glVertex3f(tx2,ty2,tz2)
    glEnd(); glLineWidth(1.0)
    ix,iy,iz=pts[-1]; sz2=2.0; glColor3f(lr,lg,lb); glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex3f(ix-sz2,iy+0.15,iz); glVertex3f(ix+sz2,iy+0.15,iz)
    glVertex3f(ix,iy+0.15,iz-sz2); glVertex3f(ix,iy+0.15,iz+sz2); glEnd()
    glPointSize(7.0); glBegin(GL_POINTS); glVertex3f(ix,iy+0.15,iz); glEnd()
    glPointSize(1.0); glLineWidth(1.0)

# ═══════════════════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════════════════
def draw_hud():
    speed=math.sqrt(vel_x**2+vel_y**2+vel_z**2)*60
    dist_to_target=math.sqrt((lander_x-target_x)**2+(lander_z-target_z)**2)
    ground_y=terrain_height(lander_x,lander_z)
    altitude=max(0.0,lander_y-ground_y)
    lv=get_land_vel_max(); rad=get_target_radius()
    wx,wz=get_wind(); wind_str=math.sqrt(wx**2+wz**2)
    on_oxy=(fuel<=0.0 and oxygen>0.0); both_empty=(fuel<=0.0 and oxygen<=0.0)
    blink=abs(math.sin(animation_time*10.0))

    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,WIN_W,0,WIN_H)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)

    ph=230 if level>=4 else 210
    glColor4f(0,0,0,0.55)
    glBegin(GL_QUADS); glVertex2f(10,WIN_H-ph); glVertex2f(400,WIN_H-ph); glVertex2f(400,WIN_H-10); glVertex2f(10,WIN_H-10); glEnd()
    glColor4f(0,0,0,0.60)
    glBegin(GL_QUADS); glVertex2f(WIN_W-225,WIN_H-150); glVertex2f(WIN_W-10,WIN_H-150); glVertex2f(WIN_W-10,WIN_H-10); glVertex2f(WIN_W-225,WIN_H-10); glEnd()
    glDisable(GL_BLEND)

    if on_oxy:   fc=(1.0,0.55+0.35*blink,0.0)
    elif fuel<10: fc=(1.0,0.1+0.7*blink,0.1)
    elif fuel<30: fc=(1.0,0.6,0.0)
    else:         fc=(0.2,0.9,0.2)
    draw_text(20,WIN_H-30,f"FUEL:   {fuel:05.1f}%",*fc)
    glColor3f(0.1,0.4,0.1)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-45); glVertex2f(385,WIN_H-45); glVertex2f(385,WIN_H-32); glVertex2f(110,WIN_H-32); glEnd()
    bc=((0.9+0.1*blink,0.5+0.3*blink,0.0) if on_oxy else (1.0,0.1,0.1) if fuel<10 else (1.0,0.6,0.0) if fuel<30 else (0.2,0.9,0.2))
    bw=min(fuel/100.0,1.0)*275; glColor3f(*bc)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-45); glVertex2f(110+bw,WIN_H-45); glVertex2f(110+bw,WIN_H-32); glVertex2f(110,WIN_H-32); glEnd()

    oc=(1.0,0.1+0.7*blink,0.1) if oxygen<10 else (1.0,0.75,0.0) if oxygen<30 else (0.2,0.6,1.0)
    draw_text(20,WIN_H-60,f"OXYGEN: {oxygen:05.1f}%",*oc)
    glColor3f(0.05,0.2,0.5)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-75); glVertex2f(385,WIN_H-75); glVertex2f(385,WIN_H-62); glVertex2f(110,WIN_H-62); glEnd()
    ocol=((1.0,0.1,0.1) if oxygen<10 else (1.0,0.75,0.0) if oxygen<30 else (0.2,0.6,1.0))
    ow=min(oxygen/100.0,1.0)*275; glColor3f(*ocol)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-75); glVertex2f(110+ow,WIN_H-75); glVertex2f(110+ow,WIN_H-62); glVertex2f(110,WIN_H-62); glEnd()

    if both_empty:   draw_text(20,WIN_H-95,"!! NO PROPELLANT - FREE FALL !!",1.0,blink*0.2,blink*0.2)
    elif on_oxy:     draw_text(20,WIN_H-95,"!! OXYGEN BACKUP - FUEL RECHARGING !!",1.0,0.5+0.4*blink,0.0)
    elif oxygen<15:  draw_text(20,WIN_H-95,"!! OXYGEN CRITICAL !!",1.0,blink*0.3,blink*0.3)
    elif fuel<15:    draw_text(20,WIN_H-95,"!! FUEL LOW !! OXYGEN BACKUP READY",1.0,0.5+0.4*blink,0.0)
    else:            draw_text(20,WIN_H-95," ",0,0,0)

    c2=(0.0,1.0,0.0) if speed<=lv else (1.0,0.3,0.1)
    draw_text(20,WIN_H-115,f"SPEED:  {speed:05.2f} u/s  (SAFE<={lv:.1f})",*c2)
    ac=(0.2,1.0,0.8) if altitude>5 else (1.0,0.6,0.0) if altitude>2 else (1.0,0.2,0.1)
    draw_text(20,WIN_H-135,f"ALT:    {altitude:05.1f} m  (above terrain)",*ac)
    draw_text(20,WIN_H-155,f"VEL  X:{vel_x:+.3f}  Y:{vel_y:+.3f}  Z:{vel_z:+.3f}",0.6,0.6,0.9)
    dc=(0.0,1.0,0.5) if dist_to_target<rad*2 else (1.0,1.0,0.3) if dist_to_target<60 else (0.8,0.8,0.8)
    draw_text(20,WIN_H-175,f"TARGET: {dist_to_target:05.1f} m away  PAD:{rad:.2f}m",*dc)
    if level>=4:
        wc=(0.3,0.6,1.0) if wind_str<0.0004 else (1.0,0.7,0.2)
        draw_text(20,WIN_H-195,f"WIND:   {wind_str*100000:.1f} uN  (Lv{level})",*wc)
        draw_text(20,WIN_H-215,"L/R:ROTATE  W/A/S/D:STRAFE  UP:THRUST  DN:RETRO",0.35,0.35,0.35)
    else:
        draw_text(20,WIN_H-195,"L/R:ROTATE  W/A/S/D:STRAFE  UP:THRUST  DN:RETRO",0.4,0.4,0.4)

    active=[]
    if key_up:  active.append("^THRUST(OXY)" if on_oxy else "^THRUST")
    if key_down: active.append("vRETRO")
    if key_w: active.append("FWD")
    if key_s: active.append("BACK")
    if key_a: active.append("LEFT")
    if key_d: active.append("RIGHT")
    if active:
        p=0.5+0.5*math.sin(animation_time*12)
        draw_text(WIN_W//2-100,WIN_H-30," | ".join(active),1.0,0.5+0.5*p,0.0)

    danger=min(1.0,(level-1)/9.0); lc=(1.0,1.0-danger*0.8,0.0)
    draw_text(WIN_W-215,WIN_H-30, f"SCORE:  {score}",1.0,0.9,0.1)
    draw_text(WIN_W-215,WIN_H-55, f"LEVEL:  {level}",*lc)
    draw_text(WIN_W-215,WIN_H-80, f"PAD R:  {rad:.2f} m",*lc)
    draw_text(WIN_W-215,WIN_H-105,f"MAX V:  {lv:.1f} u/s",*lc)
    draw_text(WIN_W-215,WIN_H-130,f"GRAV:   {diff_gravity():.4f}",0.6,0.5,0.8)

    elapsed=animation_time-new_target_flash_start
    if elapsed<5.0:
        bf=abs(math.sin(animation_time*7)); fade2=(1.0-elapsed/5.0)
        draw_text(WIN_W//2-175,WIN_H//2+60,
                  f"** NEW TARGET! {dist_to_target:.0f}m AWAY - FOLLOW THE BEACON **",bf*fade2,fade2,0.0)

    draw_text(20,60,"ESC:MENU  R:RETRY  Q:FULL RESET",0.4,0.4,0.4)

    if game_over and landing_msg:
        ok="PERFECT" in landing_msg.upper()
        c3=(0.0,1.0,0.3) if ok else (1.0,0.2,0.1)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0,0,0,0.75)
        glBegin(GL_QUADS); glVertex2f(WIN_W//2-330,WIN_H//2-100); glVertex2f(WIN_W//2+330,WIN_H//2-100)
        glVertex2f(WIN_W//2+330,WIN_H//2+60); glVertex2f(WIN_W//2-330,WIN_H//2+60); glEnd()
        glDisable(GL_BLEND)
        draw_text(WIN_W//2-len(landing_msg)*5,WIN_H//2+20,landing_msg,*c3)
        draw_text(WIN_W//2-210,WIN_H//2-10,"R: RETRY (keep score)  |  Q: FULL RESET  |  ESC: MENU",0.8,0.8,0.8)
        draw_text(WIN_W//2-120,WIN_H//2-45,f"SCORE: {score}   LEVEL: {level}",1.0,0.85,0.0)

    if not game_started and not game_over:
        draw_text(WIN_W//2-180,WIN_H//2-30,"PRESS ARROW-UP TO THRUST  |  L/R ARROWS TO ROTATE",0.9,0.9,0.2)

    glEnable(GL_DEPTH_TEST)
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

# ═══════════════════════════════════════════════════════════════════════════
#  MINI-MAP
# ═══════════════════════════════════════════════════════════════════════════
def draw_minimap():
    MW=200; MH=200; MX=WIN_W-MW-10; MY=10
    glViewport(MX,MY,MW,MH)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    half=WORLD_HALF+10; gluOrtho2D(-half,half,-half,half)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glDisable(GL_DEPTH_TEST)
    glColor3f(0.05,0.05,0.10)
    glBegin(GL_QUADS); glVertex2f(-half,-half); glVertex2f(half,-half); glVertex2f(half,half); glVertex2f(-half,half); glEnd()
    glColor3f(0.3,0.3,0.5)
    glBegin(GL_LINE_LOOP); glVertex2f(-half,-half); glVertex2f(half,-half); glVertex2f(half,half); glVertex2f(-half,half); glEnd()
    rad=get_target_radius(); danger=min(1.0,(level-1)/9.0)
    glColor3f(1.0,1.0-danger*0.8,0.0)
    glBegin(GL_LINE_LOOP)
    for s in range(32): a=2*math.pi*s/32; glVertex2f(target_x+rad*math.cos(a),target_z+rad*math.sin(a))
    glEnd()
    glColor3f(0.6,0.6,0.0); glLineWidth(1.0)
    glBegin(GL_LINES); glVertex2f(lander_x,lander_z); glVertex2f(target_x,target_z); glEnd()
    hr=math.radians(rocket_heading)
    glColor3f(0.0,1.0,1.0)
    glBegin(GL_LINES); glVertex2f(lander_x,lander_z); glVertex2f(lander_x+math.sin(hr)*18,lander_z+math.cos(hr)*18); glEnd()
    glColor3f(1.0,1.0,0.0); glPointSize(6.0)
    glBegin(GL_POINTS); glVertex2f(lander_x,lander_z); glEnd()
    glColor3f(1.0,0.5,0.0); glPointSize(9.0)
    glBegin(GL_POINTS); glVertex2f(target_x,target_z); glEnd()
    glPointSize(1.0); draw_text(-half+5,half-18,"MAP",0.6,0.6,0.8)
    glEnable(GL_DEPTH_TEST); glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glViewport(0,0,WIN_W,WIN_H)

# ═══════════════════════════════════════════════════════════════════════════
#  PHYSICS
# ═══════════════════════════════════════════════════════════════════════════
def update_physics():
    global lander_x,lander_y,lander_z,vel_x,vel_y,vel_z
    global fuel,oxygen,game_over,landing_msg,lander_tilt_z,lander_tilt_x,score,level

    if game_over or not game_started:
        lander_tilt_z*=0.92; lander_tilt_x*=0.92; return

    G=diff_gravity(); DR=diff_drag(); TU=diff_thrust_up(); TH=diff_thrust_horiz()
    FB=diff_fuel_burn(); MXH=diff_max_vel_horiz(); MXV=diff_max_vel_up()
    hr=math.radians(rocket_heading)
    fx=math.sin(hr); fz=math.cos(hr); rx=math.cos(hr); rz=-math.sin(hr)

    vel_y+=G
    hf=fuel>0; ho=oxygen>0; oo=(not hf) and ho
    any_key=key_up or key_down or key_w or key_s or key_a or key_d

    if key_up:
        if hf:  vel_y+=TU; fuel=max(0,fuel-FB)
        elif ho: vel_y+=TU*0.55; oxygen=max(0,oxygen-0.10)
    if key_down:
        if hf:  vel_y-=TU*0.45; fuel=max(0,fuel-FB*0.5)
        elif ho: vel_y-=TU*0.25; oxygen=max(0,oxygen-0.06)

    any_strafe=False
    for pressed,ddx,ddz,tilt_attr,tilt_dir in [
        (key_w, fx, fz, 'x', -1),(key_s,-fx,-fz,'x',+1),
        (key_a,-rx,-rz,'z', -1),(key_d, rx, rz,'z',+1)]:
        if pressed:
            vel_x+=ddx*TH; vel_z+=ddz*TH; any_strafe=True
            if hf:  fuel=max(0,fuel-FB*0.3)
            elif ho: oxygen=max(0,oxygen-0.04)
            if tilt_attr=='z': lander_tilt_z=max(-MAX_TILT,min(MAX_TILT,lander_tilt_z+tilt_dir*TILT_SPEED))
            else:              lander_tilt_x=max(-MAX_TILT,min(MAX_TILT,lander_tilt_x+tilt_dir*TILT_SPEED))

    if not any_strafe:
        lander_tilt_z*=(1.0-TILT_RECOVERY*0.04); lander_tilt_x*=(1.0-TILT_RECOVERY*0.04)

    if oo and any_key:
        fuel=min(100,fuel+FUEL_REGEN_RATE); oxygen=max(0,oxygen-0.10)

    wx,wz=get_wind(); vel_x+=wx; vel_z+=wz
    vel_x*=DR; vel_z*=DR
    vel_x=max(-MXH,min(MXH,vel_x)); vel_z=max(-MXH,min(MXH,vel_z)); vel_y=max(-MXV,min(MXV,vel_y))
    lander_x+=vel_x; lander_y+=vel_y; lander_z+=vel_z

    gy=terrain_height(lander_x,lander_z)
    thr=gy+0.5

    if fuel<=0 and oxygen<=0 and lander_y>thr:
        landing_msg=f"OUT OF PROPELLANT! Score:{score}"; game_over=True
        vel_x=vel_y=vel_z=0; move_target(); return

    if lander_y<=thr:
        lander_y=thr
        speed=math.sqrt(vel_x**2+vel_y**2+vel_z**2)*60
        lv=get_land_vel_max(); rad=get_target_radius()
        dist_hit=math.sqrt((lander_x-target_x)**2+(lander_z-target_z)**2)
        on_target=(dist_hit<=rad)
        if on_target and speed<=lv:
            prec=max(0.0,1.0-dist_hit/rad); mult=1.0+prec
            pts=int(max(1,int(10*level))*mult); score+=pts; level+=1
            landing_msg=f"PERFECT! +{pts}pts (x{mult:.1f}) Speed:{speed:.1f}  -> LEVEL {level}!"
            move_target()
        elif on_target:
            landing_msg=f"TOO FAST! Speed:{speed:.1f} (need<={lv:.1f}) Score:{score}"
            move_target()
        else:
            landing_msg=f"CRASHED! {dist_hit:.1f}m from target. Score:{score}"
            move_target()
        game_over=True; vel_x=vel_y=vel_z=0

# ═══════════════════════════════════════════════════════════════════════════
#  RESET
# ═══════════════════════════════════════════════════════════════════════════
def reset_game():
    global lander_x,lander_y,lander_z,vel_x,vel_y,vel_z,fuel,oxygen
    global game_started,game_over,landing_msg,gp_cam_pitch
    global lander_tilt_z,lander_tilt_x,lander_rot_y,rocket_heading
    lander_x=lander_z=0.0
    lander_y=terrain_height(0,0)+75.0
    vel_x=vel_y=vel_z=0.0; fuel=oxygen=100.0
    game_started=game_over=False; landing_msg=""
    gp_cam_pitch=22.0; lander_tilt_z=lander_tilt_x=lander_rot_y=rocket_heading=0.0

def full_reset():
    global score,level
    score=0; level=1; move_target(); reset_game()

# ═══════════════════════════════════════════════════════════════════════════
#  DISPLAY
# ═══════════════════════════════════════════════════════════════════════════
def display():
    glClearColor(0.04,0.04,0.08,1.0)
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    if current_state in ["MENU","OPTIONS"]:
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45,1.25,0.1,600.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity(); draw_interactive_scene()
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,WIN_W,0,WIN_H)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        active=main_menu if current_state=="MENU" else options_menu
        for i,opt in enumerate(active): draw_button(500,500-(i*90),opt,i)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state=="ROCKET_LIST":
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,WIN_W,0,WIN_H)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        draw_text(400,650,"SELECT SPACECRAFT",1,1,1)
        for i in range(3): draw_button(500,500-(i*100),rocket_list[i],i)
        draw_button(500,200,"START MISSION",3); draw_button(150,50," BACK ",99)
        if show_alert: draw_text(500,350,alert_message,1,0,0)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state=="ROCKET_VIEWER":
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45,1.25,0.1,100.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        glTranslatef(0,0,-25*zoom_level); glRotatef(cam_x,1,0,0); glRotatef(cam_y,0,1,0)
        if   selected_rocket_index==0: draw_jak_hound()
        elif selected_rocket_index==1: draw_eva_nation()
        elif selected_rocket_index==2: draw_jf17_thunder()
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,WIN_W,0,WIN_H)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        draw_text(20,750,f"INSPECTING: {rocket_list[selected_rocket_index]}",1,1,0)
        if selected_rocket_for_game==selected_rocket_index: draw_text(20,720,"SELECTED! | F: RESELECT",0,1,0)
        else: draw_text(20,720,"PRESS F TO SELECT THIS ROCKET",0.7,0.7,0.7)
        draw_text(20,690,"ARROWS:ROTATE | N:ZOOM IN | M:ZOOM OUT | ESC:BACK",0.5,0.5,0.5)
        draw_button(150,50," BACK ",99)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state=="GAMEPLAY":
        update_physics()
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(58,WIN_W/WIN_H,1.0,1800.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        hr=math.radians(rocket_heading); pr=math.radians(gp_cam_pitch)
        ecx=lander_x-math.sin(hr)*gp_cam_dist*math.cos(pr)
        ecy=lander_y+gp_cam_dist*math.sin(pr)
        ecz=lander_z-math.cos(hr)*gp_cam_dist*math.cos(pr)
        gluLookAt(ecx,ecy,ecz, lander_x,lander_y,lander_z, 0,1,0)
        draw_space_background()
        draw_terrain()               # <-- single glCallList(), very fast
        draw_target()
        draw_heading_indicator(); draw_wind_indicator()
        if not game_over: draw_trajectory()
        draw_new_target_arrow()
        glPushMatrix()
        glTranslatef(lander_x,lander_y,lander_z)
        glRotatef(-rocket_heading,0,1,0)
        glRotatef(lander_tilt_z,0,0,1); glRotatef(lander_tilt_x,1,0,0)
        glScalef(1.5,1.5,1.5)
        draw_selected_rocket(); draw_thrust_flame(); draw_retro_flame()
        if key_w or key_s or key_a or key_d: draw_side_flame()
        glPopMatrix()
        draw_hud(); draw_minimap()

    glutSwapBuffers()

# ═══════════════════════════════════════════════════════════════════════════
#  INPUT
# ═══════════════════════════════════════════════════════════════════════════
def keyboard(key,x,y):
    global current_state,selected_option,zoom_level
    global selected_rocket_index,selected_rocket_for_game,rocket_selected
    global show_alert,alert_message,key_w,key_a,key_s,key_d,game_started
    k=key.lower()
    if ord(key)==27:
        if current_state=="GAMEPLAY": current_state="MENU"; reset_game()
        elif current_state=="OPTIONS": current_state="MENU"; selected_option=1
        elif current_state=="ROCKET_LIST": current_state="OPTIONS"; selected_option=1; show_alert=False
        elif current_state=="ROCKET_VIEWER": current_state="ROCKET_LIST"; selected_option=selected_rocket_index
        glutPostRedisplay(); return
    if current_state=="GAMEPLAY":
        if k==b'w': key_w=True; game_started=True
        if k==b's': key_s=True; game_started=True
        if k==b'a': key_a=True; game_started=True
        if k==b'd': key_d=True; game_started=True
        if k==b'r': reset_game()
        if k==b'q': full_reset()
        glutPostRedisplay(); return
    if current_state in ["MENU","OPTIONS","ROCKET_LIST"]:
        menu_items=(main_menu if current_state=="MENU" else options_menu if current_state=="OPTIONS" else rocket_list)
        max_opt=len(menu_items)-1
        if selected_option<0 or selected_option>max_opt: selected_option=0
        if key in (b'\r',b' '):
            if current_state=="MENU":
                if selected_option==0: current_state="ROCKET_LIST"; selected_option=selected_rocket_for_game
                elif selected_option==1: current_state="OPTIONS"; selected_option=-1
                elif selected_option==2: _os._exit(0)
            elif current_state=="OPTIONS":
                if selected_option==1: current_state="ROCKET_LIST"; selected_option=-1
                elif selected_option==2: current_state="MENU"; selected_option=1
            elif current_state=="ROCKET_LIST":
                if 0<=selected_option<3: selected_rocket_index=selected_option; current_state="ROCKET_VIEWER"
                elif selected_option==3:
                    if not rocket_selected: show_alert=True; alert_message="Select your Spacecraft first!!"
                    else: full_reset(); current_state="GAMEPLAY"
    if current_state=="ROCKET_VIEWER":
        if k==b'n': zoom_level=max(0.2,zoom_level-0.1)
        elif k==b'm': zoom_level=min(3.0,zoom_level+0.1)
        elif k==b'f': selected_rocket_for_game=selected_rocket_index; rocket_selected=True
    glutPostRedisplay()

def keyboard_up(key,x,y):
    global key_w,key_a,key_s,key_d
    k=key.lower()
    if k==b'w': key_w=False
    if k==b's': key_s=False
    if k==b'a': key_a=False
    if k==b'd': key_d=False
    glutPostRedisplay()

def special_keys(key,x,y):
    global cam_x,cam_y,selected_option,gp_cam_pitch,key_up,key_down,game_started,rocket_heading
    if current_state=="GAMEPLAY":
        if   key==GLUT_KEY_UP:    key_up=True;  game_started=True
        elif key==GLUT_KEY_DOWN:  key_down=True; game_started=True
        elif key==GLUT_KEY_LEFT:  rocket_heading=(rocket_heading-3.5)%360
        elif key==GLUT_KEY_RIGHT: rocket_heading=(rocket_heading+3.5)%360
    elif current_state=="ROCKET_VIEWER":
        if   key==GLUT_KEY_LEFT:  cam_y-=5.0
        elif key==GLUT_KEY_RIGHT: cam_y+=5.0
        elif key==GLUT_KEY_UP:    cam_x-=5.0
        elif key==GLUT_KEY_DOWN:  cam_x+=5.0
    elif current_state in ["MENU","OPTIONS","ROCKET_LIST"]:
        menu_items=(main_menu if current_state=="MENU" else options_menu if current_state=="OPTIONS" else rocket_list)
        max_opt=len(menu_items)-1
        if selected_option<0: selected_option=0
        if   key==GLUT_KEY_UP:   selected_option=max(0,selected_option-1)
        elif key==GLUT_KEY_DOWN: selected_option=min(max_opt,selected_option+1)
    glutPostRedisplay()

def special_keys_up(key,x,y):
    global key_up,key_down
    if current_state=="GAMEPLAY":
        if key==GLUT_KEY_UP:   key_up=False
        if key==GLUT_KEY_DOWN: key_down=False
    glutPostRedisplay()

def mouse_click(button,state,x,y):
    global current_state,selected_option,selected_rocket_index
    global last_click_x,last_click_y,rocket_selected,show_alert,alert_message
    if button==GLUT_LEFT_BUTTON and state==GLUT_DOWN:
        last_click_x,last_click_y=x,y; ly=WIN_H-y
        if current_state=="ROCKET_LIST":
            for i in range(3):
                if 400<=x<=600 and (500-(i*100)-10)<=ly<=(500-(i*100)+25):
                    selected_rocket_index=i; current_state="ROCKET_VIEWER"
            if 400<=x<=600 and 190<=ly<=225:
                if not rocket_selected: show_alert=True; alert_message="Select your Spacecraft first!!"
                else: full_reset(); current_state="GAMEPLAY"
            if x<=250 and ly<=100: current_state="OPTIONS"; selected_option=1
        elif current_state=="ROCKET_VIEWER":
            if x<=250 and ly<=100: current_state="ROCKET_LIST"
        else:
            active=main_menu if current_state=="MENU" else options_menu
            for i,opt in enumerate(active):
                if 400<=x<=600 and (500-(i*90)-10)<=ly<=(500-(i*90)+25):
                    if selected_option==i:
                        if current_state=="MENU":
                            if i==0: current_state="ROCKET_LIST"; selected_option=selected_rocket_for_game
                            elif i==1: current_state="OPTIONS"; selected_option=-1
                            elif i==2: _os._exit(0)
                        elif current_state=="OPTIONS":
                            if i==1: current_state="ROCKET_LIST"; selected_option=-1
                            elif i==2: current_state="MENU"; selected_option=1
                    else: selected_option=i
    glutPostRedisplay()

def idle():
    global animation_time,planet_rotation_y
    animation_time+=0.01; planet_rotation_y+=0.015; glutPostRedisplay()

# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(WIN_W,WIN_H)
    glutCreateWindow(b"Lunar Descent")

    glutDisplayFunc(display); glutIdleFunc(idle)
    glutMouseFunc(mouse_click); glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboard_up); glutSpecialFunc(special_keys)
    glutSpecialUpFunc(special_keys_up)

    move_target()     # builds terrain + places first target AFTER GL context exists
    reset_game()
    glutMainLoop()

if __name__=="__main__":
    main()