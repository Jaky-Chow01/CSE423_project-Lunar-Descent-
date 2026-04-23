from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, random, os as _os

WIN_W, WIN_H = 1000, 800

current_state          = "MENU"
selected_option        = -1
selected_rocket_index  = 0
selected_rocket_for_game = -1
rocket_selected        = False
show_alert             = False
alert_message          = ""
last_click_x, last_click_y = -1000, -1000
animation_time         = 0.0
planet_rotation_y      = 0.0

cam_x, cam_y = 15.0, 0.0
zoom_level   = 1.0

main_menu    = ["START GAME", "OPTIONS", "QUIT"]
options_menu = ["TUTORIAL", "CHECK ROCKET", "BACK"]
rocket_list  = ["JakHound F-22 Raptor", "EvaNation F-15 Eagle",
                "TasroFighter JF17 Thunder", "START MISSION"]

lander_x = 0.0; lander_y = 60.0; lander_z = 0.0
vel_x = vel_y = vel_z = 0.0
fuel = 100.0; oxygen = 100.0
game_started = False
game_over    = False
landing_msg  = ""

lander_tilt_z = lander_tilt_x = lander_rot_y = 0.0
rocket_heading = 0.0

key_w = key_s = key_a = key_d = False
key_up = key_down = False

gp_cam_pitch = 25.0
gp_cam_dist  = 40.0

score = 0
level = 1
target_x = target_z = 0.0
new_target_flash_start = -999.0

MAX_TILT        = 20.0
TILT_SPEED      = 1.5
TILT_RECOVERY   = 2.5
FUEL_REGEN_RATE = 0.30   # per frame, added AFTER all consumption

# ── Difficulty helpers ─────────────────────────────────────────────────────
def diff_gravity():       return max(-0.013, -0.006 - (level-1)*0.00065)
def diff_drag():          return max(0.948,  0.980  - (level-1)*0.0034)
def diff_thrust_up():     return 0.018
def diff_thrust_horiz():  return 0.006
def diff_max_vel_horiz(): return 0.35
def diff_max_vel_up():    return 0.40
def diff_fuel_burn():     return max(0.10, 0.12 + (level-1)*0.004)
def get_land_vel_max():   return max(4.5,  20.0 - (level-1)*1.65)
def get_target_radius():  return max(0.70,  6.0  - (level-1)*0.565)
def get_target_spread():  return min(15 + level*6, 65)

def get_wind():
    if level < 4: return 0.0, 0.0
    strength = (level-3)*0.00025
    angle = math.radians(animation_time*4.0)
    return math.cos(angle)*strength, math.sin(angle)*strength

# ── Terrain ────────────────────────────────────────────────────────────────
terrain_cubes = []

def generate_terrain():
    global terrain_cubes
    terrain_cubes = []
    random.seed(level*7+13)
    for gx in range(-10,11):
        for gz in range(-10,11):
            x=gx*12.0; z=gz*12.0; h=random.uniform(0.5,2.5); grey=random.uniform(0.30,0.55)
            terrain_cubes.append((x,-h/2-1.0,z,11.8,h,11.8,grey,grey,grey*1.05))
    for _ in range(80):
        x=random.uniform(-110,110); z=random.uniform(-110,110)
        if math.sqrt((x-target_x)**2+(z-target_z)**2)<get_target_radius()+5: continue
        sx=random.uniform(1.0,5.0); sy=random.uniform(1.5,8.0); sz=random.uniform(1.0,5.0)
        grey=random.uniform(0.25,0.50)
        terrain_cubes.append((x,sy/2,z,sx,sy,sz,grey,grey,grey*1.1))

def move_target():
    global target_x, target_z, new_target_flash_start
    spread = get_target_spread()
    for _ in range(200):
        tx=random.uniform(-spread,spread); tz=random.uniform(-spread,spread)
        if math.sqrt(tx**2+tz**2)>8.0:
            target_x,target_z=tx,tz; break
    new_target_flash_start = animation_time
    generate_terrain()

star_data = []
for _ in range(700):
    _tx,_ty=random.uniform(-100,100),random.uniform(-60,60)
    star_data.append([_tx,_ty,random.uniform(-150,-20),random.uniform(0.5,0.9),_tx,_ty])

# ═══════════════════════════════════════════════════════════════════════════
#  DRAWING HELPERS
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

def draw_cylinder_new(br,tr,h,sl=32,st=4): gluCylinder(gluNewQuadric(),br,tr,h,sl,st)
def draw_sphere_new(r,sl=32,st=32):        gluSphere(gluNewQuadric(),r,sl,st)
def draw_disk_new(inner,outer,sl=32):      gluCylinder(gluNewQuadric(),outer,inner,0.01,sl,1)
def draw_cone_new(base,h,sl=32):           draw_cylinder_new(base,0.0,h,sl)

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
    for nx,nz in [(0,0),(-0.18,0),(0.18,0),(0,-0.18),(0,0.18)]:
        glColor3f(0.30,0.03,0.03); glPushMatrix(); glTranslatef(nx,-0.05,nz)
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
#  SCENE
# ═══════════════════════════════════════════════════════════════════════════
def draw_terrain():
    for (x,y,z,sx,sy,sz,r,g,b) in terrain_cubes:
        glColor3f(r,g,b); glPushMatrix()
        glTranslatef(x,y,z); glScalef(sx,sy,sz); glutSolidCube(1.0); glPopMatrix()

def draw_target():
    cx,cz=target_x,target_z; radius=get_target_radius()
    pulse=0.5+0.5*math.sin(animation_time*4.0); danger=min(1.0,(level-1)/9.0)
    tr=1.0; tg=1.0-danger*0.8; tb=0.0
    for ring_r,lw in [(radius+1.5,3.0),(radius,2.0),(radius*0.5,2.0)]:
        glColor3f(tr,tg*(pulse*0.8+0.2),tb); glLineWidth(lw)
        glBegin(GL_LINE_LOOP)
        for s in range(64): a=2*math.pi*s/64; glVertex3f(cx+ring_r*math.cos(a),0.06,cz+ring_r*math.sin(a))
        glEnd()
    glColor3f(1.0,0.3,0.0)
    glBegin(GL_QUADS)
    glVertex3f(cx-0.3,0.09,cz-0.3); glVertex3f(cx+0.3,0.09,cz-0.3)
    glVertex3f(cx+0.3,0.09,cz+0.3); glVertex3f(cx-0.3,0.09,cz+0.3); glEnd()
    glColor3f(tr,tg,tb); glLineWidth(2.5)
    glBegin(GL_LINES)
    glVertex3f(cx-(radius+2),0.07,cz); glVertex3f(cx+(radius+2),0.07,cz)
    glVertex3f(cx,0.07,cz-(radius+2)); glVertex3f(cx,0.07,cz+(radius+2)); glEnd()
    glColor3f(1.0,0.6,0.0); glLineWidth(1.5)
    for tick in range(8):
        a=2*math.pi*tick/8+animation_time*0.8
        glBegin(GL_LINES)
        glVertex3f(cx+radius*0.75*math.cos(a),0.07,cz+radius*0.75*math.sin(a))
        glVertex3f(cx+radius*1.10*math.cos(a),0.07,cz+radius*1.10*math.sin(a)); glEnd()
    beacon_h=18.0+pulse*4.0; glColor3f(tr,tg,tb); glLineWidth(1.5)
    glBegin(GL_LINES); glVertex3f(cx,0.1,cz); glVertex3f(cx,beacon_h,cz); glEnd()
    glLineWidth(1.0)

def draw_new_target_arrow():
    elapsed=animation_time-new_target_flash_start
    if elapsed>3.0: return
    fade=1.0-elapsed/3.0; blink=abs(math.sin(animation_time*8.0)); alpha=fade*blink
    dx=target_x-lander_x; dz=target_z-lander_z
    dist=math.sqrt(dx**2+dz**2)
    if dist<0.01: return
    nx=dx/dist; nz=dz/dist
    ax=lander_x+nx*6; az=lander_z+nz*6; ay=lander_y+2.0
    glLineWidth(4.0); glColor3f(alpha,alpha*0.85,0.0)
    glBegin(GL_LINES); glVertex3f(lander_x,ay,lander_z); glVertex3f(ax,ay,az); glEnd()
    glPointSize(10.0); glBegin(GL_POINTS); glVertex3f(ax,ay,az); glEnd()
    glPointSize(1.0); glLineWidth(1.0)

def draw_wind_indicator():
    if level<4: return
    wx,wz=get_wind(); strength=math.sqrt(wx**2+wz**2)
    if strength<1e-6: return
    nx=wx/strength; nz=wz/strength; scale=min(strength*80000,1.0)
    glColor3f(0.4*scale,0.6*scale,1.0); glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex3f(lander_x,lander_y+4,lander_z)
    glVertex3f(lander_x+nx*3,lander_y+4,lander_z+nz*3); glEnd()
    glLineWidth(1.0)

def draw_space_background():
    q=gluNewQuadric(); glPointSize(2.0); glBegin(GL_POINTS)
    random.seed(7)
    for _ in range(500):
        angle=random.uniform(0,2*math.pi); elev=random.uniform(-math.pi/2,math.pi/2); dist=350.0
        glColor3f(random.uniform(0.6,1.0),random.uniform(0.6,1.0),random.uniform(0.7,1.0))
        glVertex3f(dist*math.cos(elev)*math.cos(angle),dist*math.sin(elev),dist*math.cos(elev)*math.sin(angle))
    glEnd()
    glPushMatrix(); glRotatef(planet_rotation_y*0.1,0,1,0); glTranslatef(300,80,0)
    glColor3f(1.0,0.9,0.3); gluSphere(q,18,24,24); glPopMatrix()
    glPushMatrix(); glRotatef(planet_rotation_y*0.3,0,1,0); glTranslatef(200,30,-100)
    glColor3f(0.1,0.4,0.8); gluSphere(q,10,24,24)
    glColor3f(0.9,0.9,0.9); glPushMatrix(); glRotatef(planet_rotation_y*2,0,1,0)
    gluSphere(q,10.2,8,8); glPopMatrix(); glPopMatrix()
    glPushMatrix(); glRotatef(planet_rotation_y*0.2,0,1,0); glTranslatef(-180,-20,150)
    glColor3f(0.7,0.25,0.1); gluSphere(q,6,20,20); glPopMatrix()

def draw_heading_indicator():
    hr=math.radians(rocket_heading); fx=math.sin(hr)*4.0; fz=math.cos(hr)*4.0
    glColor3f(0.0,1.0,1.0); glLineWidth(2.5)
    glBegin(GL_LINES); glVertex3f(lander_x,0.3,lander_z); glVertex3f(lander_x+fx,0.3,lander_z+fz); glEnd()
    glLineWidth(1.0)

def draw_thrust_flame():
    if not key_up: return
    if fuel<=0 and oxygen<=0: return
    on_oxy=(fuel<=0 and oxygen>0)
    flame=0.5+0.5*math.sin(animation_time*15.0)
    if on_oxy: glColor3f(0.4,0.6+0.3*flame,1.0)
    else:      glColor3f(1.0,0.5+0.3*flame,0.0)
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

def draw_trajectory():
    px,py,pz=lander_x,lander_y,lander_z; vx,vy,vz=vel_x,vel_y,vel_z
    sim_fuel=fuel; sim_oxy=oxygen
    hr=math.radians(rocket_heading)
    fwd_x=math.sin(hr); fwd_z=math.cos(hr); right_x=math.cos(hr); right_z=-math.sin(hr)
    DRAG_S=diff_drag(); GRAV_S=diff_gravity(); MXH=diff_max_vel_horiz(); MXV=diff_max_vel_up()
    points=[(px,py,pz)]
    for _ in range(400):
        vy+=GRAV_S
        s_have_fuel=sim_fuel>0.0; s_have_oxy=sim_oxy>0.0
        s_on_oxy=(not s_have_fuel) and s_have_oxy
        any_key=key_w or key_s or key_a or key_d or key_up or key_down
        if key_up:
            if s_have_fuel: vy+=diff_thrust_up(); sim_fuel=max(0,sim_fuel-diff_fuel_burn())
            elif s_have_oxy: vy+=diff_thrust_up()*0.55; sim_oxy=max(0,sim_oxy-0.10)
        if key_down:
            if s_have_fuel: vy-=diff_thrust_up()*0.45; sim_fuel=max(0,sim_fuel-diff_fuel_burn()*0.5)
            elif s_have_oxy: vy-=diff_thrust_up()*0.25; sim_oxy=max(0,sim_oxy-0.06)
        if key_w:
            vx+=fwd_x*diff_thrust_horiz(); vz+=fwd_z*diff_thrust_horiz()
            if s_have_fuel: sim_fuel=max(0,sim_fuel-diff_fuel_burn()*0.3)
            elif s_have_oxy: sim_oxy=max(0,sim_oxy-0.04)
        if key_s:
            vx-=fwd_x*diff_thrust_horiz(); vz-=fwd_z*diff_thrust_horiz()
            if s_have_fuel: sim_fuel=max(0,sim_fuel-diff_fuel_burn()*0.3)
            elif s_have_oxy: sim_oxy=max(0,sim_oxy-0.04)
        if key_a:
            vx-=right_x*diff_thrust_horiz(); vz-=right_z*diff_thrust_horiz()
            if s_have_fuel: sim_fuel=max(0,sim_fuel-diff_fuel_burn()*0.3)
            elif s_have_oxy: sim_oxy=max(0,sim_oxy-0.04)
        if key_d:
            vx+=right_x*diff_thrust_horiz(); vz+=right_z*diff_thrust_horiz()
            if s_have_fuel: sim_fuel=max(0,sim_fuel-diff_fuel_burn()*0.3)
            elif s_have_oxy: sim_oxy=max(0,sim_oxy-0.04)
        # regen in simulation too
        if s_on_oxy and any_key:
            sim_fuel=min(100,sim_fuel+FUEL_REGEN_RATE)
            sim_oxy=max(0,sim_oxy-0.10)
        wx,wz=get_wind(); vx+=wx; vz+=wz
        vx*=DRAG_S; vz*=DRAG_S
        vx=max(-MXH,min(MXH,vx)); vz=max(-MXH,min(MXH,vz)); vy=max(-MXV,min(MXV,vy))
        px+=vx; py+=vy; pz+=vz
        if py<=0.5: py=0.5; points.append((px,py,pz)); break
        points.append((px,py,pz))
    if len(points)<2: return
    impact_speed=math.sqrt(vx**2+vy**2+vz**2)*60; lv=get_land_vel_max()
    lr,lg,lb=(0.2,1.0,0.3) if impact_speed<=lv else (1.0,0.85,0.0) if impact_speed<=lv*1.5 else (1.0,0.2,0.1)
    glLineWidth(1.8); glBegin(GL_LINE_STRIP)
    for idx,(tx,ty,tz) in enumerate(points):
        fade=1.0-(idx/len(points))*0.7; glColor3f(lr*fade,lg*fade,lb*fade); glVertex3f(tx,ty,tz)
    glEnd(); glLineWidth(1.0)
    ix,iy,iz=points[-1]; sz2=1.5; glColor3f(lr,lg,lb); glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex3f(ix-sz2,iy+0.1,iz); glVertex3f(ix+sz2,iy+0.1,iz)
    glVertex3f(ix,iy+0.1,iz-sz2); glVertex3f(ix,iy+0.1,iz+sz2); glEnd()
    glPointSize(7.0); glBegin(GL_POINTS); glVertex3f(ix,iy+0.1,iz); glEnd()
    glPointSize(1.0); glLineWidth(1.0)

# ═══════════════════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════════════════
def draw_hud():
    speed=math.sqrt(vel_x**2+vel_y**2+vel_z**2)*60
    dist_to_target=math.sqrt((lander_x-target_x)**2+(lander_z-target_z)**2)
    lv=get_land_vel_max(); rad=get_target_radius()
    wx,wz=get_wind(); wind_str=math.sqrt(wx**2+wz**2)
    on_oxygen_backup=(fuel<=0.0 and oxygen>0.0)
    both_empty=(fuel<=0.0 and oxygen<=0.0)
    blink=abs(math.sin(animation_time*10.0))

    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,WIN_W,0,WIN_H)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)

    panel_h=225 if level>=4 else 205
    glColor4f(0,0,0,0.55)
    glBegin(GL_QUADS); glVertex2f(10,WIN_H-panel_h); glVertex2f(395,WIN_H-panel_h); glVertex2f(395,WIN_H-10); glVertex2f(10,WIN_H-10); glEnd()
    glColor4f(0,0,0,0.60)
    glBegin(GL_QUADS); glVertex2f(WIN_W-220,WIN_H-145); glVertex2f(WIN_W-10,WIN_H-145); glVertex2f(WIN_W-10,WIN_H-10); glVertex2f(WIN_W-220,WIN_H-10); glEnd()
    glDisable(GL_BLEND)

    # ── FUEL bar ──────────────────────────────────────────────────────────
    if on_oxygen_backup:
        fc_label=(1.0,0.55+0.35*blink,0.0)
    elif fuel<10: fc_label=(1.0,0.1+0.7*blink,0.1)
    elif fuel<30: fc_label=(1.0,0.6,0.0)
    else:         fc_label=(0.2,0.9,0.2)
    draw_text(20,WIN_H-30,f"FUEL:   {fuel:05.1f}%",*fc_label)
    glColor3f(0.1,0.4,0.1)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-45); glVertex2f(375,WIN_H-45); glVertex2f(375,WIN_H-32); glVertex2f(110,WIN_H-32); glEnd()
    if on_oxygen_backup: bar_col=(0.9+0.1*blink,0.5+0.3*blink,0.0)
    elif fuel<10:        bar_col=(1.0,0.1,0.1)
    elif fuel<30:        bar_col=(1.0,0.6,0.0)
    else:                bar_col=(0.2,0.9,0.2)
    bw=min(fuel/100.0,1.0)*265; glColor3f(*bar_col)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-45); glVertex2f(110+bw,WIN_H-45); glVertex2f(110+bw,WIN_H-32); glVertex2f(110,WIN_H-32); glEnd()

    # ── OXYGEN bar ────────────────────────────────────────────────────────
    if oxygen<10:   oc_label=(1.0,0.1+0.7*blink,0.1)
    elif oxygen<30: oc_label=(1.0,0.75,0.0)
    else:           oc_label=(0.2,0.6,1.0)
    draw_text(20,WIN_H-60,f"OXYGEN: {oxygen:05.1f}%",*oc_label)
    glColor3f(0.05,0.2,0.5)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-75); glVertex2f(375,WIN_H-75); glVertex2f(375,WIN_H-62); glVertex2f(110,WIN_H-62); glEnd()
    if oxygen<10:   oxy_col=(1.0,0.1,0.1)
    elif oxygen<30: oxy_col=(1.0,0.75,0.0)
    else:           oxy_col=(0.2,0.6,1.0)
    ow=min(oxygen/100.0,1.0)*265; glColor3f(*oxy_col)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-75); glVertex2f(110+ow,WIN_H-75); glVertex2f(110+ow,WIN_H-62); glVertex2f(110,WIN_H-62); glEnd()

    # ── Status warning ────────────────────────────────────────────────────
    if both_empty:
        draw_text(20,WIN_H-95,"!! NO PROPELLANT - FREE FALL !!",1.0,blink*0.2,blink*0.2)
    elif on_oxygen_backup:
        draw_text(20,WIN_H-95,"!! OXYGEN BACKUP - FUEL RECHARGING !!",1.0,0.5+0.4*blink,0.0)
    elif oxygen<15:
        draw_text(20,WIN_H-95,"!! OXYGEN CRITICAL !!",1.0,blink*0.3,blink*0.3)
    elif fuel<15:
        draw_text(20,WIN_H-95,"!! FUEL LOW !! OXYGEN BACKUP READY",1.0,0.5+0.4*blink,0.0)
    else:
        draw_text(20,WIN_H-95," ",0,0,0)

    col2=(0.0,1.0,0.0) if speed<=lv else (1.0,0.3,0.1)
    draw_text(20,WIN_H-115,f"SPEED:  {speed:05.2f} u/s  (SAFE<={lv:.1f})",*col2)
    draw_text(20,WIN_H-135,f"ALT:    {max(0,lander_y):05.1f} m",0.9,0.9,0.9)
    draw_text(20,WIN_H-155,f"VEL  X:{vel_x:+.3f}  Y:{vel_y:+.3f}  Z:{vel_z:+.3f}",0.6,0.6,0.9)
    dc=(0.0,1.0,0.5) if dist_to_target<rad*2 else (1.0,1.0,0.3) if dist_to_target<30 else (0.8,0.8,0.8)
    draw_text(20,WIN_H-175,f"TARGET: {dist_to_target:05.1f} m  PAD:{rad:.2f}m",*dc)

    if level>=4:
        wc=(0.3,0.6,1.0) if wind_str<0.0004 else (1.0,0.7,0.2)
        draw_text(20,WIN_H-195,f"WIND:   {wind_str*100000:.1f} uN  (Lv{level})",*wc)
        draw_text(20,WIN_H-215,"L/R:ROTATE | W/A/S/D:STRAFE | UP:THRUST | DN:RETRO",0.35,0.35,0.35)
    else:
        draw_text(20,WIN_H-195,"L/R:ROTATE | W/A/S/D:STRAFE | UP:THRUST | DN:RETRO",0.4,0.4,0.4)

    active=[]
    if key_up:   active.append("^THRUST(OXY)" if on_oxygen_backup else "^THRUST")
    if key_down: active.append("vRETRO")
    if key_w: active.append("FWD")
    if key_s: active.append("BACK")
    if key_a: active.append("LEFT")
    if key_d: active.append("RIGHT")
    if active:
        p=0.5+0.5*math.sin(animation_time*12)
        draw_text(WIN_W//2-100,WIN_H-30," | ".join(active),1.0,0.5+0.5*p,0.0)

    danger=min(1.0,(level-1)/9.0); lc=(1.0,1.0-danger*0.8,0.0)
    draw_text(WIN_W-210,WIN_H-30, f"SCORE:  {score}",1.0,0.9,0.1)
    draw_text(WIN_W-210,WIN_H-55, f"LEVEL:  {level}",*lc)
    draw_text(WIN_W-210,WIN_H-80, f"PAD R:  {rad:.2f} m",*lc)
    draw_text(WIN_W-210,WIN_H-105,f"MAX V:  {lv:.1f} u/s",*lc)
    draw_text(WIN_W-210,WIN_H-130,f"GRAV:   {diff_gravity():.4f}",0.6,0.5,0.8)

    elapsed=animation_time-new_target_flash_start
    if elapsed<3.0:
        bf=abs(math.sin(animation_time*7)); fade2=(1.0-elapsed/3.0)
        draw_text(WIN_W//2-145,WIN_H//2+60,f"** NEW TARGET! {dist_to_target:.0f}m AWAY **",bf*fade2,fade2,0.0)

    draw_text(20,60,"ESC:MENU  R:RETRY(keep score)  Q:FULL RESET | Land on the bullseye!",0.4,0.4,0.4)

    if game_over and landing_msg:
        is_perfect="PERFECT" in landing_msg.upper()
        is_prop="PROPELLANT" in landing_msg.upper()
        col3=(0.0,1.0,0.3) if is_perfect else (1.0,0.15,0.05) if is_prop else (1.0,0.2,0.1)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0,0,0,0.72)
        glBegin(GL_QUADS)
        glVertex2f(WIN_W//2-320,WIN_H//2-95); glVertex2f(WIN_W//2+320,WIN_H//2-95)
        glVertex2f(WIN_W//2+320,WIN_H//2+55); glVertex2f(WIN_W//2-320,WIN_H//2+55); glEnd()
        glDisable(GL_BLEND)
        draw_text(WIN_W//2-len(landing_msg)*5,WIN_H//2+18,landing_msg,*col3)
        draw_text(WIN_W//2-200,WIN_H//2-12,"R: RETRY (keep score) | Q: FULL RESET | ESC: MENU",0.8,0.8,0.8)
        draw_text(WIN_W//2-125,WIN_H//2-45,f"SCORE: {score}   LEVEL: {level}",1.0,0.85,0.0)
        nxt_pad=max(0.70,6.0-level*0.565); nxt_vel=max(4.5,20.0-level*1.65)
        draw_text(WIN_W//2-195,WIN_H//2-70,
                  f"NEXT: pad={nxt_pad:.2f}m  max_speed={nxt_vel:.1f}  wind={'YES' if level>=4 else 'NO'}",0.6,0.6,0.6)

    if not game_started and not game_over:
        draw_text(WIN_W//2-175,WIN_H//2-30,"PRESS ARROW-UP TO THRUST  |  L/R ARROWS TO ROTATE",0.9,0.9,0.2)

    glEnable(GL_DEPTH_TEST)
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

# ═══════════════════════════════════════════════════════════════════════════
#  MINI-MAP
# ═══════════════════════════════════════════════════════════════════════════
def draw_minimap():
    MAP_W=180; MAP_H=180; MAP_X=WIN_W-MAP_W-10; MAP_Y=10
    glViewport(MAP_X,MAP_Y,MAP_W,MAP_H)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(-120,120,-120,120)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glDisable(GL_DEPTH_TEST)
    glColor3f(0.05,0.05,0.10)
    glBegin(GL_QUADS); glVertex2f(-120,-120); glVertex2f(120,-120); glVertex2f(120,120); glVertex2f(-120,120); glEnd()
    glColor3f(0.3,0.3,0.5)
    glBegin(GL_LINE_LOOP); glVertex2f(-120,-120); glVertex2f(120,-120); glVertex2f(120,120); glVertex2f(-120,120); glEnd()
    rad=get_target_radius(); danger=min(1.0,(level-1)/9.0)
    glColor3f(1.0,1.0-danger*0.8,0.0)
    glBegin(GL_LINE_LOOP)
    for s in range(32): a=2*math.pi*s/32; glVertex2f(target_x+rad*math.cos(a),target_z+rad*math.sin(a))
    glEnd()
    glColor3f(1.0,0.6,0.0)
    glBegin(GL_LINES); glVertex2f(lander_x,lander_z); glVertex2f(target_x,target_z); glEnd()
    hr=math.radians(rocket_heading)
    glColor3f(0.0,1.0,1.0)
    glBegin(GL_LINES); glVertex2f(lander_x,lander_z); glVertex2f(lander_x+math.sin(hr)*8,lander_z+math.cos(hr)*8); glEnd()
    glColor3f(1.0,1.0,0.0); glPointSize(6.0)
    glBegin(GL_POINTS); glVertex2f(lander_x,lander_z); glEnd(); glPointSize(1.0)
    draw_text(-115,108,"MAP",0.6,0.6,0.8)
    glEnable(GL_DEPTH_TEST); glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    glViewport(0,0,WIN_W,WIN_H)

# ═══════════════════════════════════════════════════════════════════════════
#  PHYSICS  ── fuel regen: runs AFTER all thrust, never written to in oxy mode
# ═══════════════════════════════════════════════════════════════════════════
def update_physics():
    global lander_x, lander_y, lander_z, vel_x, vel_y, vel_z
    global fuel, oxygen, game_over, landing_msg
    global lander_tilt_z, lander_tilt_x, score, level

    if game_over or not game_started:
        lander_tilt_z *= 0.92; lander_tilt_x *= 0.92
        return

    GRAV  = diff_gravity();      DRAG_F = diff_drag()
    TU    = diff_thrust_up();    TH     = diff_thrust_horiz()
    FB    = diff_fuel_burn();    MXH    = diff_max_vel_horiz()
    MXV   = diff_max_vel_up()

    hr      = math.radians(rocket_heading)
    fwd_x   = math.sin(hr);  fwd_z   = math.cos(hr)
    right_x = math.cos(hr);  right_z = -math.sin(hr)

    vel_y += GRAV

    # Decide mode once, clearly
    have_fuel   = fuel   > 0.0
    have_oxygen = oxygen > 0.0
    on_oxy_mode = (not have_fuel) and have_oxygen

    any_thrust_key = key_up or key_down or key_w or key_s or key_a or key_d

    # ── Main thruster (↑) ─────────────────────────────────────────────────
    if key_up:
        if have_fuel:
            vel_y += TU
            fuel   = max(0.0, fuel - FB)       # normal: burn fuel only
        elif have_oxygen:
            vel_y += TU * 0.55
            oxygen = max(0.0, oxygen - 0.10)   # backup: burn ONLY oxygen, fuel untouched

    # ── Retro thruster (↓) ────────────────────────────────────────────────
    if key_down:
        if have_fuel:
            vel_y -= TU * 0.45
            fuel   = max(0.0, fuel - FB * 0.5)
        elif have_oxygen:
            vel_y -= TU * 0.25
            oxygen = max(0.0, oxygen - 0.06)   # backup: burn ONLY oxygen

    # ── Strafing (W/A/S/D) ────────────────────────────────────────────────
    any_strafe = False
    if key_w:
        vel_x += fwd_x * TH;  vel_z += fwd_z * TH
        lander_tilt_x = max(-MAX_TILT, lander_tilt_x - TILT_SPEED)
        any_strafe = True
        if have_fuel:       fuel   = max(0.0, fuel   - FB * 0.3)
        elif have_oxygen:   oxygen = max(0.0, oxygen - 0.04)   # fuel untouched
    if key_s:
        vel_x -= fwd_x * TH;  vel_z -= fwd_z * TH
        lander_tilt_x = min(MAX_TILT, lander_tilt_x + TILT_SPEED)
        any_strafe = True
        if have_fuel:       fuel   = max(0.0, fuel   - FB * 0.3)
        elif have_oxygen:   oxygen = max(0.0, oxygen - 0.04)
    if key_a:
        vel_x -= right_x * TH;  vel_z -= right_z * TH
        lander_tilt_z = max(-MAX_TILT, lander_tilt_z - TILT_SPEED)
        any_strafe = True
        if have_fuel:       fuel   = max(0.0, fuel   - FB * 0.3)
        elif have_oxygen:   oxygen = max(0.0, oxygen - 0.04)
    if key_d:
        vel_x += right_x * TH;  vel_z += right_z * TH
        lander_tilt_z = min(MAX_TILT, lander_tilt_z + TILT_SPEED)
        any_strafe = True
        if have_fuel:       fuel   = max(0.0, fuel   - FB * 0.3)
        elif have_oxygen:   oxygen = max(0.0, oxygen - 0.04)

    if not any_strafe:
        lander_tilt_z *= (1.0 - TILT_RECOVERY * 0.04)
        lander_tilt_x *= (1.0 - TILT_RECOVERY * 0.04)

    # ── FUEL REGEN ────────────────────────────────────────────────────────
    # Runs LAST after all thrust blocks.
    # In oxy mode no thrust block ever writes to fuel, so this +0.30 is
    # never cancelled — fuel will visibly climb every frame a key is held.
    if on_oxy_mode and any_thrust_key:
        fuel   = min(100.0, fuel + FUEL_REGEN_RATE)
        oxygen = max(0.0,   oxygen - 0.10)   # regen costs extra oxygen

    # ── Wind, drag, velocity cap ──────────────────────────────────────────
    wx, wz = get_wind()
    vel_x += wx;  vel_z += wz
    vel_x *= DRAG_F;  vel_z *= DRAG_F
    vel_x  = max(-MXH, min(MXH, vel_x))
    vel_z  = max(-MXH, min(MXH, vel_z))
    vel_y  = max(-MXV, min(MXV, vel_y))

    lander_x += vel_x
    lander_y += vel_y
    lander_z += vel_z

    # ── Both propellants gone mid-air ─────────────────────────────────────
    if fuel <= 0.0 and oxygen <= 0.0 and lander_y > 0.5:
        landing_msg = f"OUT OF PROPELLANT! Total system failure.  Score:{score}"
        game_over = True;  vel_x = vel_y = vel_z = 0.0
        move_target();  return

    # ── Ground collision ──────────────────────────────────────────────────
    if lander_y <= 0.5:
        lander_y = 0.5
        speed    = math.sqrt(vel_x**2 + vel_y**2 + vel_z**2) * 60
        lv       = get_land_vel_max()
        rad      = get_target_radius()
        dist_hit = math.sqrt((lander_x - target_x)**2 + (lander_z - target_z)**2)
        on_target = (dist_hit <= rad)
        if on_target and speed <= lv:
            precision  = max(0.0, 1.0 - dist_hit / rad)
            multiplier = 1.0 + precision
            pts        = int(max(1, int(10 * level)) * multiplier)
            score     += pts;  level += 1
            landing_msg = f"PERFECT! +{pts}pts (x{multiplier:.1f}) Speed:{speed:.1f}  -> LEVEL {level}!"
            move_target()
        elif on_target:
            landing_msg = f"TOO FAST! Speed:{speed:.1f} (need<={lv:.1f})  Score:{score}"
            move_target()
        else:
            landing_msg = f"MISSED TARGET! {dist_hit:.1f}m off  Speed:{speed:.1f}  Score:{score}"
            move_target()
        game_over = True;  vel_x = vel_y = vel_z = 0.0

# ═══════════════════════════════════════════════════════════════════════════
#  RESET
# ═══════════════════════════════════════════════════════════════════════════
def reset_game():
    global lander_x,lander_y,lander_z,vel_x,vel_y,vel_z,fuel,oxygen
    global game_started,game_over,landing_msg,gp_cam_pitch
    global lander_tilt_z,lander_tilt_x,lander_rot_y,rocket_heading
    lander_x=lander_z=0.0; lander_y=60.0; vel_x=vel_y=vel_z=0.0
    fuel=oxygen=100.0; game_started=game_over=False; landing_msg=""
    gp_cam_pitch=25.0; lander_tilt_z=lander_tilt_x=lander_rot_y=rocket_heading=0.0

def full_reset():
    global score,level
    score=0; level=1; move_target(); reset_game()

# ═══════════════════════════════════════════════════════════════════════════
#  DISPLAY
# ═══════════════════════════════════════════════════════════════════════════
def display():
    glClearColor(0.04,0.04,0.08,1.0); glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT); glEnable(GL_DEPTH_TEST)

    if current_state in ["MENU","OPTIONS"]:
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45,1.25,0.1,500.0)
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
        if selected_rocket_index==0: draw_jak_hound()
        elif selected_rocket_index==1: draw_eva_nation()
        elif selected_rocket_index==2: draw_jf17_thunder()
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,WIN_W,0,WIN_H)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        draw_text(20,750,f"INSPECTING: {rocket_list[selected_rocket_index]}",1,1,0)
        if selected_rocket_for_game==selected_rocket_index:
            draw_text(20,720,"SELECTED! | F: RESELECT",0,1,0)
        else:
            draw_text(20,720,"PRESS F TO SELECT THIS ROCKET",0.7,0.7,0.7)
        draw_text(20,690,"ARROWS:ROTATE | N:ZOOM IN | M:ZOOM OUT | ESC:BACK",0.5,0.5,0.5)
        draw_button(150,50," BACK ",99)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()

    elif current_state=="GAMEPLAY":
        update_physics()
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(55,WIN_W/WIN_H,0.1,1000.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        hr=math.radians(rocket_heading); pr=math.radians(gp_cam_pitch)
        ecx=lander_x-math.sin(hr)*gp_cam_dist*math.cos(pr)
        ecy=lander_y+gp_cam_dist*math.sin(pr)
        ecz=lander_z-math.cos(hr)*gp_cam_dist*math.cos(pr)
        gluLookAt(ecx,ecy,ecz,lander_x,lander_y,lander_z,0,1,0)
        draw_space_background(); draw_terrain(); draw_target()
        draw_heading_indicator(); draw_wind_indicator()
        if not game_over: draw_trajectory()
        draw_new_target_arrow()
        glPushMatrix()
        glTranslatef(lander_x,lander_y,lander_z)
        glRotatef(-rocket_heading,0,1,0); glRotatef(lander_tilt_z,0,0,1); glRotatef(lander_tilt_x,1,0,0)
        glScalef(1.5,1.5,1.5); draw_selected_rocket(); draw_thrust_flame(); draw_retro_flame()
        if key_w or key_s or key_a or key_d: draw_side_flame()
        glPopMatrix()
        draw_hud(); draw_minimap()

    glutSwapBuffers()

# ═══════════════════════════════════════════════════════════════════════════
#  INPUT
# ═══════════════════════════════════════════════════════════════════════════
def keyboard(key,x,y):
    global current_state,selected_option,zoom_level,selected_rocket_index,selected_rocket_for_game
    global rocket_selected,show_alert,alert_message,key_w,key_a,key_s,key_d,game_started
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
        menu_items=main_menu if current_state=="MENU" else options_menu if current_state=="OPTIONS" else rocket_list
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
        elif key==GLUT_KEY_LEFT:  rocket_heading=(rocket_heading-3.0)%360
        elif key==GLUT_KEY_RIGHT: rocket_heading=(rocket_heading+3.0)%360
    elif current_state=="ROCKET_VIEWER":
        if   key==GLUT_KEY_LEFT:  cam_y-=5.0
        elif key==GLUT_KEY_RIGHT: cam_y+=5.0
        elif key==GLUT_KEY_UP:    cam_x-=5.0
        elif key==GLUT_KEY_DOWN:  cam_x+=5.0
    elif current_state in ["MENU","OPTIONS","ROCKET_LIST"]:
        menu_items=main_menu if current_state=="MENU" else options_menu if current_state=="OPTIONS" else rocket_list
        max_opt=len(menu_items)-1
        if selected_option<0: selected_option=0
        if key==GLUT_KEY_UP:    selected_option=max(0,selected_option-1)
        elif key==GLUT_KEY_DOWN: selected_option=min(max_opt,selected_option+1)
    glutPostRedisplay()

def special_keys_up(key,x,y):
    global key_up,key_down
    if current_state=="GAMEPLAY":
        if key==GLUT_KEY_UP:   key_up=False
        if key==GLUT_KEY_DOWN: key_down=False
    glutPostRedisplay()

def mouse_click(button,state,x,y):
    global current_state,selected_option,selected_rocket_index,last_click_x,last_click_y
    global rocket_selected,show_alert,alert_message
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

def main():
    move_target()
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(WIN_W,WIN_H)
    glutCreateWindow(b"Lunar Descent")
    glutDisplayFunc(display); glutIdleFunc(idle)
    glutMouseFunc(mouse_click); glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboard_up); glutSpecialFunc(special_keys)
    glutSpecialUpFunc(special_keys_up)
    glutMainLoop()

if __name__=="__main__":
    main()