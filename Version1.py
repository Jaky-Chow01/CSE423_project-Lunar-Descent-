from OpenGL.GL import *
from OpenGL.GLUT import *  
from OpenGL.GLUT import GLUT_BITMAP_9_BY_15  
import math, random, os as _os

WIN_W, WIN_H = 1000, 800

#Global State
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

cam_rx, cam_ry = 15.0, 0.0
zoom_level     = 1.0
tutorial_scroll = 0

main_menu    = ["START GAME", "OPTIONS", "QUIT"]
options_menu = ["TUTORIAL", "CHECK ROCKET", "BACK"]
rocket_list  = ["JakHound F-22", "EvaNation F-15", "JF17 Thunder", "START MISSION"]

tutorial_text = [
    "LUNAR DESCENT - How to Play",
    "",
    "GAME OVERVIEW",
    "Pilot a rocket to safely land on the lunar surface. Manage",
    "limited fuel and oxygen resources while navigating treacherous",
    "terrain. Achieve perfect landings to advance through levels.",
    "",
    "BASIC CONTROLS",
    "SPACE - Main Thrust (uses fuel, switches to oxygen when empty)",
    "DOWN ARROW - Retro-thrust (slows descent, uses less fuel)",
    "W/A/S/D - Move forward/left/backward/right (combine for diagonals)",
    "LEFT/RIGHT ARROWS - Rotate camera around lander",
    "PAGE UP/PAGE DOWN - Adjust camera pitch",
    "C - Toggle autopilot (auto-lands if possible)",
    "",
    "RESOURCE MANAGEMENT",
    "FUEL (Primary) - Starts at 100%, regenerates when idle",
    "OXYGEN (Backup) - Activates when fuel depletes (55% efficiency)",
    "When both empty: Free fall with no recovery possible!",
    "",
    "LANDING OBJECTIVES",
    "Land INSIDE the orange target rings (cyan on minimap)",
    "Land at or BELOW the safe speed (shown in green in HUD)",
    "Speed requirements get stricter at higher levels",
    "PERFECT LANDING = On target + Safe speed = More points + Level up",
    "",
    "LANDING OUTCOMES",
    "PERFECT! - On target + safe speed (earn bonus, advance level)",
    "TOO FAST! - On target but exceeding speed limit (mission failed)",
    "CRASHED! - Landed outside target zone (mission failed)",
    "",
    "HUD INFORMATION",
    "Left Panel: Fuel, Oxygen, Speed, Altitude, Velocity, Target info",
    "Right Panel: Score, Level, Pad radius",
    "Center: Shows which controls are currently pressed",
    "Minimap (top-right): Map of terrain, target (yellow), you (cyan)",
    "",
    "DIFFICULTY PROGRESSION",
    "Each level increases: Gravity, control difficulty, strictness",
    "Target pad shrinks, safe speed decreases, wind appears at level 4+",
    "Higher levels = 10x points per level * precision multiplier",
    "",
    "PRO TIPS",
    "Thrust early when far from target - build approach gradually",
    "Use retro-thrust for efficient descent (50% fuel cost)",
    "Strafe movement (WASD) is cheapest (30% fuel cost)",
    "Let fuel regenerate - stop using controls when not needed",
    "Watch the minimap for approach vector (cyan arrow)",
    "Minimize final touchdown speed - nearly vertical landing best",
    "Try autopilot to learn proper landing technique",
    "",
    "SCORING SYSTEM",
    "Base Points = 10 x Current_Level",
    "Precision Bonus = 1.0x (pad edge) to 2.0x (pad center)",
    "Final Score = Base x Multiplier (higher precision = more points)",
    "",
    "QUICK CHECKLIST",
    "1. Select your rocket from the menu",
    "2. Practice on lower levels first",
    "3. Master thrust + horizontal movement combinations",
    "4. Learn to use retro-thrust efficiently",
    "5. Aim for PERFECT! landings for bonus points",
    "6. Progress to harder levels",
    "",
    "READY TO FLY? ESC to return to menu and start your mission!",
    "May your landings be smooth and your fuel abundant!"
]

# Lander 
lander_x = 0.0;  lander_y = 80.0;  lander_z = 0.0
vel_x = vel_y = vel_z = 0.0
fuel = 100.0;  oxygen = 100.0
game_started = False;  game_over = False;  landing_msg = ""
lander_tilt_z = lander_tilt_x = rocket_heading = 0.0
gp_cam_pitch = 22.0;  gp_cam_dist = 45.0
gp_cam_yaw   = 0.0

score = 0;  level = 1
target_x = target_z = 0.0;  target_surface_y = 0.0
new_target_flash_start = -999.0
MAX_TILT = 40.0;  TILT_SPEED = 1.6;  TILT_RECOVERY = 2.8;  FUEL_REGEN = 0.28
autopilot = False  # Pressing C activates AutoPilot


KEY_WINDOW    = 6          
key_last_seen = {}         

def _key_press(token):
    
    global game_started
    key_last_seen[token] = frame_count
    if current_state == "GAMEPLAY":
        game_started = True

def key_held(token):
    return key_last_seen.get(token, -9999) >= frame_count - KEY_WINDOW

# Convenience aliases
def key_space_held(): return key_held(b'\x00sp')
def key_dn_held():    return key_held(b'\x00dn')
def key_w_held():     return key_held(b'w')
def key_s_held():     return key_held(b's')
def key_a_held():     return key_held(b'a')
def key_d_held():     return key_held(b'd')
def key_left_held():  return key_held(b'\x00lt')
def key_right_held(): return key_held(b'\x00rt')


#DIFFICULTY

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
    s = (level-3)*0.00028;  a = math.radians(animation_time*4.0)
    return math.cos(a)*s, math.sin(a)*s


# TERRAIN

WORLD_HALF   = 320
TERRAIN_DIVS = 90
_terrain_dl  = None
_mountains   = []
_craters     = []
_terrain_tris = []   # cached terrain triangles (no display lists)

def terrain_height(wx, wz):
    y = 0.0
    for (cx, cz, rad, pk) in _mountains:
        d = math.sqrt((wx-cx)**2 + (wz-cz)**2)
        if d < rad:
            t = 1.0 - d/rad;  y += pk*t*t*(3.0-2.0*t)
    for (cx, cz, rad, dep) in _craters:
        d = math.sqrt((wx-cx)**2 + (wz-cz)**2)
        if d < rad:
            t = d/rad
            y += -dep*(1.0-t*t) + dep*0.42*math.exp(-((t-0.86)/0.07)**2)
    return y

def _build_terrain_dl():
    global _terrain_dl, _terrain_tris
    step = (WORLD_HALF*2)/TERRAIN_DIVS;  cols = TERRAIN_DIVS+1
    verts = []
    for row in range(cols):
        for col in range(cols):
            wx = -WORLD_HALF + col*step;  wz = -WORLD_HALF + row*step
            verts.append((wx, terrain_height(wx, wz), wz))

     
    _terrain_tris = []
    for row in range(TERRAIN_DIVS):
        for col in range(TERRAIN_DIVS):
            i00=row*cols+col; i10=i00+1; i01=i00+cols; i11=i01+1
            def emit(ia, ib, ic):
                va,vb,vc = verts[ia],verts[ib],verts[ic]
                ux,uy,uz = vb[0]-va[0],vb[1]-va[1],vb[2]-va[2]
                vx2,vy2,vz2 = vc[0]-va[0],vc[1]-va[1],vc[2]-va[2]
                nx=uy*vz2-uz*vy2; ny=uz*vx2-ux*vz2; nz2=ux*vy2-uy*vx2
                ln=math.sqrt(nx*nx+ny*ny+nz2*nz2)
                if ln>1e-9: nx/=ln; ny/=ln; nz2/=ln
                
                avg_y = (va[1] + vb[1] + vc[1]) / 3.0
                t=max(0.0,min(1.0,(avg_y+18)/62.0)); b=0.18+t*0.36
                col=(b*0.96,b,b*1.06)
                _terrain_tris.append((col, va, vb, vc))
            emit(i00,i10,i01); emit(i10,i11,i01)

    
    _terrain_dl = None

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


#  PROJECTION & CAMERA

def set_perspective(fovy_deg, aspect, znear, zfar):
    
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    f = 1.0/math.tan(math.radians(fovy_deg)*0.5)
    top = znear / f
    bottom = -top
    right = top * aspect
    left = -right

    rl = (right - left)
    tb = (top - bottom)
    fn = (zfar - znear)
    if rl == 0 or tb == 0 or fn == 0:
        return

   
    m = [
        (2.0 * znear) / rl, 0.0, 0.0, 0.0,
        0.0, (2.0 * znear) / tb, 0.0, 0.0,
        (right + left) / rl, (top + bottom) / tb, -(zfar + znear) / fn, -1.0,
        0.0, 0.0, -(2.0 * zfar * znear) / fn, 0.0
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
    glScalef(2.0/WIN_W,2.0/WIN_H,-0.001)
    glTranslatef(-WIN_W/2.0,-WIN_H/2.0,0.0)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()

def _ortho_pop():
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()


#GL PRIMITIVES

def draw_cylinder(r,h,sides=16):
    step=2*math.pi/sides
    glBegin(GL_QUAD_STRIP)
    for i in range(sides+1):
        a=i*step; ca=math.cos(a); sa=math.sin(a)
        glVertex3f(r*ca,0,r*sa); glVertex3f(r*ca,h,r*sa)
    glEnd()
    for yy,ny in [(0,-1),(h,1)]:
        rr = list(range(sides, -1, -1)) if ny < 0 else list(range(sides + 1))
        if len(rr) < 2:
            continue
        glBegin(GL_TRIANGLES)
        for k in range(len(rr) - 1):
            i0 = rr[k]; i1 = rr[k + 1]
            a0 = i0 * step; a1 = i1 * step
            glVertex3f(0,yy,0)
            glVertex3f(r*math.cos(a0),yy,r*math.sin(a0))
            glVertex3f(r*math.cos(a1),yy,r*math.sin(a1))
        glEnd()

def draw_cone(r,h,sides=16):
    step=2*math.pi/sides

    glBegin(GL_TRIANGLES)
    for i in range(sides):
        a0=i*step; a1=(i+1)*step
        
        glVertex3f(0,h,0)
        glVertex3f(r*math.cos(a0),0,r*math.sin(a0))
        glVertex3f(r*math.cos(a1),0,r*math.sin(a1))
    glEnd()
    
    glBegin(GL_TRIANGLES)
    for i in range(sides):
        a0=(sides-i)*step; a1=(sides-i-1)*step
        glVertex3f(0,0,0)
        glVertex3f(r*math.cos(a0),0,r*math.sin(a0))
        glVertex3f(r*math.cos(a1),0,r*math.sin(a1))
    glEnd()

def draw_sphere(r,stacks=10,slices=14):
    for i in range(stacks):
        lat0=math.pi*(-0.5+i/stacks); lat1=math.pi*(-0.5+(i+1)/stacks)
        z0,zr0=math.sin(lat0),math.cos(lat0); z1,zr1=math.sin(lat1),math.cos(lat1)
        glBegin(GL_QUAD_STRIP)
        for j in range(slices+1):
            lng=2*math.pi*j/slices; x=math.cos(lng); y=math.sin(lng)
            glVertex3f(r*x*zr0,r*z0,r*y*zr0)
            glVertex3f(r*x*zr1,r*z1,r*y*zr1)
        glEnd()

def draw_box(sx,sy,sz):
    hx,hy,hz=sx/2,sy/2,sz/2
    glBegin(GL_QUADS)
    for vts,nm in [
        ([(hx,hy,hz),(hx,-hy,hz),(hx,-hy,-hz),(hx,hy,-hz)],(1,0,0)),
        ([(-hx,hy,-hz),(-hx,-hy,-hz),(-hx,-hy,hz),(-hx,hy,hz)],(-1,0,0)),
        ([(-hx,hy,-hz),(hx,hy,-hz),(hx,hy,hz),(-hx,hy,hz)],(0,1,0)),
        ([(-hx,-hy,hz),(hx,-hy,hz),(hx,-hy,-hz),(-hx,-hy,-hz)],(0,-1,0)),
        ([(-hx,hy,hz),(hx,hy,hz),(hx,-hy,hz),(-hx,-hy,hz)],(0,0,1)),
        ([(hx,hy,-hz),(-hx,hy,-hz),(-hx,-hy,-hz),(hx,-hy,-hz)],(0,0,-1))]:
        for v in vts: glVertex3f(*v)
    glEnd()

def draw_disk(r,sides=16):

    step = 2*math.pi/sides
    glBegin(GL_TRIANGLES)
    for i in range(sides):
        a0=i*step; a1=(i+1)*step
        glVertex3f(0,0,0)
        glVertex3f(r*math.cos(a0),0,r*math.sin(a0))
        glVertex3f(r*math.cos(a1),0,r*math.sin(a1))
    glEnd()


#  TEXT & BUTTONS

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
    if sel:  draw_text(x-tw/2,y,text,1,1,1); glColor3f(1,0.2,0.2)
    else:    draw_text(x-tw/2,y,text,0.7,0.1,0.1); glColor3f(0.4,0,0)
    glBegin(GL_LINES)
    glVertex2f(x0,y0); glVertex2f(x1,y0); glVertex2f(x1,y0); glVertex2f(x1,y1); glVertex2f(x1,y1); glVertex2f(x0,y1); glVertex2f(x0,y1); glVertex2f(x0,y0)
    glEnd()

#  MENU BACKGROUND

star_data=[]
for i in range(600):
    _tx,_ty=random.uniform(-100,100),random.uniform(-60,60)
    star_data.append([_tx,_ty,random.uniform(-150,-20),random.uniform(0.5,0.9),_tx,_ty])

def draw_interactive_scene():
    set_perspective(45,WIN_W/WIN_H,0.1,600.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    glTranslatef(0,0,-60)
    glPointSize(3.0); glBegin(GL_POINTS)
    mx=(last_click_x-500)/6.0; my=(400-last_click_y)/6.0
    for i,s in enumerate(star_data):
        blink=0.2+0.6*abs(math.sin(animation_time*5+i))
        glColor3f(blink*s[3],blink*s[3],blink*s[3])
        dx,dy=mx-s[0],my-s[1]; dist=math.sqrt(dx**2+dy**2)
        if dist<15: s[0]+=dx*0.05; s[1]+=dy*0.05
        else:       s[0]+=(s[4]-s[0])*0.02; s[1]+=(s[5]-s[1])*0.02
        glVertex3f(s[0],s[1],s[2])
    glEnd()
    glPushMatrix(); glTranslatef(22,-14,15)
    glRotatef(planet_rotation_y+(last_click_x-500)/40.0,0,1,0)
    glRotatef((last_click_y-400)/40.0,1,0,0)
    glColor3f(0.8,0.8,0.82); draw_sphere(8,16,24)
    glPushMatrix(); glRotatef(animation_time*8,1,1,0)
    glColor3f(0.3,0.3,0.32); draw_sphere(8.1,6,8); glPopMatrix()
    glPopMatrix()


#ROCKET MODELS

def draw_jak_hound():
    glColor3f(0.14,0.14,0.16); draw_cylinder(0.30,2.10,8)
    glColor3f(0.85,0.60,0.10)
    glPushMatrix(); glTranslatef(0,1.65,0); draw_cylinder(0.31,0.22,8); glPopMatrix()
    glColor3f(0.05,0.55,0.95)
    glPushMatrix(); glTranslatef(0,1.52,0.33); draw_sphere(0.09,6,8); glPopMatrix()
    glColor3f(0.75,0.55,0.08)
    for py in [0.30,0.65,1.00,1.35]:
        glPushMatrix(); glTranslatef(0,py,0.29); draw_box(0.34,0.025,0.04); glPopMatrix()
    glColor3f(0.18,0.18,0.20)
    glPushMatrix(); glTranslatef(0,2.10,0); draw_cone(0.28,0.95,8); glPopMatrix()
    glColor3f(0.80,0.60,0.10)
    glPushMatrix(); glTranslatef(0,3.05,0); draw_sphere(0.07,6,8); glPopMatrix()
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
    glPushMatrix(); glTranslatef(0,3.30,0); draw_sphere(0.08,6,8); glPopMatrix()
    glColor3f(0.85,0.45,0.70); draw_disk(0.42,16)
    for i,col in enumerate([(0.80,0.35,0.60),(0.90,0.45,0.70),(0.80,0.35,0.60),(0.90,0.45,0.70)]):
        glColor3f(*col); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.38,0.10,0); draw_box(0.55,0.85,0.06); glPopMatrix()
    glColor3f(0.55,0.15,0.80)
    glPushMatrix(); glTranslatef(0,0.05,0); draw_cylinder(0.44,0.05,32); glPopMatrix()

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
    glPushMatrix(); glTranslatef(0,2.90,0); draw_sphere(0.06,6,8); glPopMatrix()
    glColor3f(0.45,0.04,0.04); draw_disk(0.34,6)
    for i in range(4):
        glColor3f(0.50,0.05,0.05); glPushMatrix(); glRotatef(i*90,0,1,0)
        glTranslatef(0.44,0.15,0); draw_box(0.40,0.70,0.06); glPopMatrix()
    flame=0.5+0.5*math.sin(animation_time*8.0)
    glColor3f(1.0,0.4+0.3*flame,0.0)
    glPushMatrix(); glTranslatef(0,-0.05,0); draw_cone(0.15,0.5+0.4*flame,12); glPopMatrix()

def draw_selected_rocket():
    if   selected_rocket_for_game==0: draw_jak_hound()
    elif selected_rocket_for_game==1: draw_eva_nation()
    elif selected_rocket_for_game==2: draw_jf17_thunder()
    else: draw_jak_hound()


#  SPACE BACKGROUND & TERRAIN

def draw_space_background():
    glPointSize(2.0); glBegin(GL_POINTS)
    random.seed(7)
    for i in range(500):
        ang=random.uniform(0,2*math.pi); el=random.uniform(-math.pi/2,math.pi/2)
        glColor3f(random.uniform(0.6,1.0),random.uniform(0.6,1.0),random.uniform(0.7,1.0))
        glVertex3f(450*math.cos(el)*math.cos(ang),450*math.sin(el),450*math.cos(el)*math.sin(ang))
    glEnd()
    glPushMatrix(); glRotatef(planet_rotation_y*0.1,0,1,0); glTranslatef(400,100,0)
    glColor3f(1.0,0.9,0.3); draw_sphere(22,12,18); glPopMatrix()
    glPushMatrix(); glRotatef(planet_rotation_y*0.3,0,1,0); glTranslatef(260,40,-130)
    glColor3f(0.1,0.4,0.8); draw_sphere(12,10,16)
    glColor3f(0.9,0.9,0.9); glPushMatrix(); glRotatef(planet_rotation_y*2,0,1,0)
    draw_sphere(12.3,5,8); glPopMatrix(); glPopMatrix()
    glPushMatrix(); glRotatef(planet_rotation_y*0.2,0,1,0); glTranslatef(-220,-25,180)
    glColor3f(0.7,0.25,0.1); draw_sphere(7,8,12); glPopMatrix()

def draw_terrain():
    
    if not _terrain_tris:
        return
    glBegin(GL_TRIANGLES)
    for (r,g,b),v0,v1,v2 in _terrain_tris:
        glColor3f(r,g,b); glVertex3f(*v0)
        glColor3f(r,g,b); glVertex3f(*v1)
        glColor3f(r,g,b); glVertex3f(*v2)
    glEnd()


#TARGET & INDICATORS

def draw_target():
    cx,cz=target_x,target_z; sy=terrain_height(cx,cz)
    rad=get_target_radius(); pulse=0.5+0.5*math.sin(animation_time*4.0)
    danger=min(1.0,(level-1)/9.0); tg=1.0-danger*0.8
    for ring_r,lw in [(rad+2.0,3.0),(rad,2.2),(rad*0.5,2.0)]:
        glColor3f(1.0,tg*(pulse*0.8+0.2),0.0)
        glBegin(GL_LINES)
        for s in range(64):
            a=2*math.pi*s/64; next_a=2*math.pi*(s+1)/64; wx2=cx+ring_r*math.cos(a); wz2=cz+ring_r*math.sin(a); wx3=cx+ring_r*math.cos(next_a); wz3=cz+ring_r*math.sin(next_a)
            glVertex3f(wx2,terrain_height(wx2,wz2)+0.15,wz2); glVertex3f(wx3,terrain_height(wx3,wz3)+0.15,wz3)
        glEnd()
    glColor3f(1.0,tg,0.0)
    glBegin(GL_LINES)
    glVertex3f(cx-(rad+3),sy+0.15,cz); glVertex3f(cx+(rad+3),sy+0.15,cz)
    glVertex3f(cx,sy+0.15,cz-(rad+3)); glVertex3f(cx,sy+0.15,cz+(rad+3))
    glEnd()
    glColor3f(1.0,0.6,0.0)
    for tick in range(8):
        a=2*math.pi*tick/8+animation_time*0.8
        glBegin(GL_LINES)
        glVertex3f(cx+rad*0.75*math.cos(a),sy+0.15,cz+rad*0.75*math.sin(a))
        glVertex3f(cx+rad*1.12*math.cos(a),sy+0.15,cz+rad*1.12*math.sin(a))
        glEnd()
    bh=sy+40.0+pulse*6.0
    glColor3f(1.0,tg,0.0)
    glBegin(GL_LINES); glVertex3f(cx,sy+0.1,cz); glVertex3f(cx,bh,cz); glEnd()
    glPointSize(10.0); glColor3f(1.0,1.0,0.2*pulse)
    glBegin(GL_POINTS); glVertex3f(cx,bh,cz); glEnd()
    glPointSize(1.0)

def draw_new_target_arrow():
    elapsed=animation_time-new_target_flash_start
    if elapsed>5.0: return
    fade=1.0-elapsed/5.0; alpha=fade*abs(math.sin(animation_time*8.0))
    dx=target_x-lander_x; dz=target_z-lander_z
    dist=math.sqrt(dx**2+dz**2)
    if dist<0.01: return
    nx2=dx/dist; nz2=dz/dist
    ax=lander_x+nx2*8; az=lander_z+nz2*8; ay=lander_y+3.0
    glColor3f(alpha,alpha*0.85,0.0)
    glBegin(GL_LINES); glVertex3f(lander_x,ay,lander_z); glVertex3f(ax,ay,az); glEnd()
    glPointSize(13.0); glBegin(GL_POINTS); glVertex3f(ax,ay,az); glEnd()
    glPointSize(1.0)

def draw_heading_indicator():
    sy=terrain_height(lander_x,lander_z)
    hr=math.radians(rocket_heading)
    ex2=lander_x+math.sin(hr)*6; ez2=lander_z+math.cos(hr)*6
    glColor3f(0.0,1.0,1.0)
    glBegin(GL_LINES)
    glVertex3f(lander_x,sy+0.35,lander_z)
    glVertex3f(ex2,terrain_height(ex2,ez2)+0.35,ez2)
    glEnd()

def draw_thrust_flame():
    if not key_space_held(): return
    if fuel<=0 and oxygen<=0: return
    on_oxy=(fuel<=0 and oxygen>0); flame=0.5+0.5*math.sin(animation_time*15.0)
    glColor3f(0.4,0.6+0.3*flame,1.0) if on_oxy else glColor3f(1.0,0.5+0.3*flame,0.0)
    glPushMatrix(); glTranslatef(0,-0.5,0); draw_cone(0.3,1.0+0.6*flame,12); glPopMatrix()

def draw_retro_flame():
    if not key_dn_held() or (fuel<=0 and oxygen<=0): return
    flame=0.4+0.4*math.sin(animation_time*15.0); glColor3f(0.5,0.8+0.2*flame,1.0)
    glPushMatrix(); glTranslatef(0,2.5,0); glRotatef(180,1,0,0); draw_cone(0.2,0.6+0.4*flame,12); glPopMatrix()


#  TRAJECTORY

def draw_trajectory():
    px,py,pz=lander_x,lander_y,lander_z
    vx,vy,vz=vel_x,vel_y,vel_z; sf,so=fuel,oxygen
    # Movement direction is screen/world aligned (WASD)
    fwx,fwz = 0.0, 1.0
    rtx,rtz = 1.0, 0.0
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
            # Thrust also pushes in the currently held WASD direction
            dx = dz = 0.0
            if kw: dx += fwx; dz += fwz
            if ks: dx -= fwx; dz -= fwz
            if kk: dx += rtx; dz += rtz
            if ka: dx -= rtx; dz -= rtz
            dl = math.sqrt(dx*dx + dz*dz)
            if dl > 1e-9:
                dx /= dl; dz /= dl
                vx += dx * (TU * 0.60)
                vz += dz * (TU * 0.60)
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
    glBegin(GL_LINE_STRIP)
    for idx,(tx2,ty2,tz2) in enumerate(pts):
        fade=1.0-(idx/len(pts))*0.7
        glColor3f(lr*fade,lg*fade,lb*fade); glVertex3f(tx2,ty2,tz2)
    glEnd()
    ix,iy,iz=pts[-1]; glColor3f(lr,lg,lb)
    glBegin(GL_LINES)
    glVertex3f(ix-2,iy+0.15,iz); glVertex3f(ix+2,iy+0.15,iz)
    glVertex3f(ix,iy+0.15,iz-2); glVertex3f(ix,iy+0.15,iz+2)
    glEnd()
    glPointSize(7.0); glBegin(GL_POINTS); glVertex3f(ix,iy+0.15,iz); glEnd()
    glPointSize(1.0)


#  MINIMAP

def draw_minimap():
    MW=200; MH=200; MX_vp=WIN_W-MW-10; MY_vp=10
    
    old_depth = glIsEnabled(GL_DEPTH_TEST)
    glViewport(MX_vp,MY_vp,MW,MH)
    half=float(WORLD_HALF+10)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    glScalef(1.0/half,1.0/half,1.0)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    glColor3f(0.04,0.04,0.10)
    glBegin(GL_QUADS)
    glVertex2f(-half,-half); glVertex2f(half,-half)
    glVertex2f(half,half);   glVertex2f(-half,half); glEnd()
    glColor3f(0.4,0.4,0.6)
    glBegin(GL_LINES)
    glVertex2f(-half,-half); glVertex2f(half,-half); glVertex2f(half,-half); glVertex2f(half,half); glVertex2f(half,half); glVertex2f(-half,half); glVertex2f(-half,half); glVertex2f(-half,-half)
    glEnd()
    danger=min(1.0,(level-1)/9.0); ring_r=max(get_target_radius(),8.0)
    glColor3f(1.0,1.0-danger*0.8,0.0)
    glBegin(GL_LINES)
    for s in range(32):
        a=2*math.pi*s/32; next_a=2*math.pi*(s+1)/32
        glVertex2f(target_x+ring_r*math.cos(a),target_z+ring_r*math.sin(a)); glVertex2f(target_x+ring_r*math.cos(next_a),target_z+ring_r*math.sin(next_a))
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
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    if old_depth:
        glEnable(GL_DEPTH_TEST)
    else:
        glDisable(GL_DEPTH_TEST)
    
    glViewport(0,0,WIN_W,WIN_H)


#  HUD

def draw_hud():
    speed=math.sqrt(vel_x**2+vel_y**2+vel_z**2)*60
    dtgt=math.sqrt((lander_x-target_x)**2+(lander_z-target_z)**2)
    alt=max(0.0,lander_y-terrain_height(lander_x,lander_z))
    lv=get_land_vel_max(); rad=get_target_radius()
    on_oxy=(fuel<=0 and oxygen>0); both_empty=(fuel<=0 and oxygen<=0)
    blink=abs(math.sin(animation_time*10.0))
    _ortho_push(); glDisable(GL_DEPTH_TEST)
    
    glColor3f(0,0,0)
    glBegin(GL_QUADS)
    glVertex2f(10,WIN_H-235); glVertex2f(408,WIN_H-235)
    glVertex2f(408,WIN_H-10); glVertex2f(10,WIN_H-10); glEnd()
    glColor3f(0,0,0)
    glBegin(GL_QUADS)
    glVertex2f(WIN_W-225,WIN_H-155); glVertex2f(WIN_W-10,WIN_H-155)
    glVertex2f(WIN_W-10,WIN_H-10);   glVertex2f(WIN_W-225,WIN_H-10); glEnd()
    fc=(1.0,0.55+0.35*blink,0.0) if on_oxy else (1.0,0.1+0.7*blink,0.1) if fuel<10 else (1.0,0.6,0.0) if fuel<30 else (0.2,0.9,0.2)
    draw_text(20,WIN_H-30,f"FUEL:   {fuel:05.1f}%",*fc)
    glColor3f(0.1,0.4,0.1)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-45); glVertex2f(392,WIN_H-45); glVertex2f(392,WIN_H-32); glVertex2f(110,WIN_H-32); glEnd()
    bw=min(fuel/100.0,1.0)*282; bc=(0.9,0.5,0.0) if on_oxy else (1.0,0.1,0.1) if fuel<10 else (1.0,0.6,0.0) if fuel<30 else (0.2,0.9,0.2)
    glColor3f(*bc)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-45); glVertex2f(110+bw,WIN_H-45); glVertex2f(110+bw,WIN_H-32); glVertex2f(110,WIN_H-32); glEnd()
    oc=(1.0,0.1+0.7*blink,0.1) if oxygen<10 else (1.0,0.75,0.0) if oxygen<30 else (0.2,0.6,1.0)
    draw_text(20,WIN_H-60,f"OXYGEN: {oxygen:05.1f}%",*oc)
    glColor3f(0.05,0.2,0.5)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-75); glVertex2f(392,WIN_H-75); glVertex2f(392,WIN_H-62); glVertex2f(110,WIN_H-62); glEnd()
    ow=min(oxygen/100.0,1.0)*282; ocol=(1.0,0.1,0.1) if oxygen<10 else (1.0,0.75,0.0) if oxygen<30 else (0.2,0.6,1.0)
    glColor3f(*ocol)
    glBegin(GL_QUADS); glVertex2f(110,WIN_H-75); glVertex2f(110+ow,WIN_H-75); glVertex2f(110+ow,WIN_H-62); glVertex2f(110,WIN_H-62); glEnd()
    if both_empty:   draw_text(20,WIN_H-95,"!! NO PROPELLANT - FREE FALL !!",1.0,blink*0.2,blink*0.2)
    elif on_oxy:     draw_text(20,WIN_H-95,"!! OXYGEN BACKUP - FUEL RECHARGING !!",1.0,0.5+0.4*blink,0.0)
    elif oxygen<15:  draw_text(20,WIN_H-95,"!! OXYGEN CRITICAL !!",1.0,blink*0.3,blink*0.3)
    elif fuel<15:    draw_text(20,WIN_H-95,"!! FUEL LOW - OXYGEN BACKUP READY !!",1.0,0.5+0.4*blink,0.0)
    else:            draw_text(20,WIN_H-95," ",0,0,0)
    c2=(0.0,1.0,0.0) if speed<=lv else (1.0,0.3,0.1)
    draw_text(20,WIN_H-115,f"SPEED:  {speed:05.2f} u/s  (safe <= {lv:.1f})",*c2)
    ac=(0.2,1.0,0.8) if alt>5 else (1.0,0.6,0.0) if alt>2 else (1.0,0.2,0.1)
    draw_text(20,WIN_H-135,f"ALT:    {alt:05.1f} m  (above terrain)",*ac)
    draw_text(20,WIN_H-155,f"VEL  X:{vel_x:+.3f}  Y:{vel_y:+.3f}  Z:{vel_z:+.3f}",0.6,0.6,0.9)
    dc=(0.0,1.0,0.5) if dtgt<rad*2 else (1.0,1.0,0.3) if dtgt<60 else (0.8,0.8,0.8)
    draw_text(20,WIN_H-175,f"TARGET: {dtgt:05.1f} m away  PAD: {rad:.2f}m",*dc)
    draw_text(20,WIN_H-197,"HOLD: SPACE=Thrust   WASD=Move (diagonals work)",0.4,0.4,0.4)
    draw_text(20,WIN_H-212,"ARROWS=Camera orbit/pitch  PgUp/PgDn=Camera pitch  All keys combinable!",0.35,0.35,0.35)
    active=[]
    if key_space_held(): active.append("^THRUST(OXY)" if on_oxy else "^THRUST")
    if key_dn_held():    active.append("vRETRO")
    if key_w_held():     active.append("UP")
    if key_s_held():     active.append("DOWN")
    if key_a_held():     active.append("LEFT")
    if key_d_held():     active.append("RIGHT")
    if active:
        p=0.5+0.5*math.sin(animation_time*12)
        draw_text(WIN_W//2-len(" | ".join(active))*5,WIN_H-30," | ".join(active),1.0,0.5+0.5*p,0.0)
    danger=min(1.0,(level-1)/9.0); lc=(1.0,1.0-danger*0.8,0.0)
    draw_text(WIN_W-215,WIN_H-30, f"SCORE:  {score}",1.0,0.9,0.1)
    draw_text(WIN_W-215,WIN_H-55, f"LEVEL:  {level}",*lc)
    draw_text(WIN_W-215,WIN_H-80, f"PAD R:  {rad:.2f} m",*lc)
    draw_text(WIN_W-215,WIN_H-105,f"MAX V:  {lv:.1f} u/s",*lc)
    draw_text(WIN_W-215,WIN_H-130,f"GRAV:   {diff_gravity():.4f}",0.6,0.5,0.8)
   
    glColor3f(0,0,0)
    glBegin(GL_QUADS)
    glVertex2f(WIN_W-225,WIN_H-170); glVertex2f(WIN_W-10,WIN_H-170)
    glVertex2f(WIN_W-10,WIN_H-155); glVertex2f(WIN_W-225,WIN_H-155); glEnd()
    if autopilot:
        ap_blink=abs(math.sin(animation_time*6.0))
        draw_text(WIN_W-215,WIN_H-167,"[C] AUTO PILOT: ON ",0.0,1.0,0.2+0.6*ap_blink)
    else:
        draw_text(WIN_W-215,WIN_H-167,"[C] AUTO PILOT: OFF",0.5,0.5,0.5)
    elapsed=animation_time-new_target_flash_start
    if elapsed<5.0:
        bf=abs(math.sin(animation_time*7)); fade2=1.0-elapsed/5.0
        draw_text(WIN_W//2-175,WIN_H//2+60,f"** NEW TARGET! {dtgt:.0f}m AWAY **",bf*fade2,fade2,0.0)
    draw_text(20,50,"ESC:MENU  R:RETRY  Q:FULL RESET",0.4,0.4,0.4)
    if game_over and landing_msg:
        ok="PERFECT" in landing_msg.upper(); c3=(0.0,1.0,0.3) if ok else (1.0,0.2,0.1)
        glColor3f(0,0,0)
        glBegin(GL_QUADS)
        glVertex2f(WIN_W//2-335,WIN_H//2-105); glVertex2f(WIN_W//2+335,WIN_H//2-105)
        glVertex2f(WIN_W//2+335,WIN_H//2+65);  glVertex2f(WIN_W//2-335,WIN_H//2+65); glEnd()
        draw_text(WIN_W//2-len(landing_msg)*5,WIN_H//2+22,landing_msg,*c3)
        draw_text(WIN_W//2-210,WIN_H//2-8,"R: RETRY (keep score)  |  Q: FULL RESET  |  ESC: MENU",0.8,0.8,0.8)
        draw_text(WIN_W//2-120,WIN_H//2-42,f"SCORE: {score}   LEVEL: {level}",1.0,0.85,0.0)
    if not game_started and not game_over:
        draw_text(WIN_W//2-215,WIN_H//2-30,"HOLD SPACE to lift off  |  WASD + Arrows all combinable",0.9,0.9,0.2)
    glEnable(GL_DEPTH_TEST); _ortho_pop()


#  PHYSICS  

def update_physics():
    global lander_x,lander_y,lander_z,vel_x,vel_y,vel_z
    global fuel,oxygen,game_over,landing_msg,lander_tilt_z,lander_tilt_x
    global score,level,rocket_heading,autopilot

    if game_over or not game_started:
        lander_tilt_z*=0.92; lander_tilt_x*=0.92; return

    G=diff_gravity(); DR=diff_drag(); TU=diff_thrust_up()
    TH=diff_thrust_horiz(); FB=diff_fuel_burn(); MX=diff_max_vel()

  
    fwx,fwz = 0.0, 1.0
    rtx,rtz = 1.0, 0.0

    vel_y+=G
    hf=fuel>0; ho=oxygen>0; oo=(not hf) and ho
    any_key=(key_space_held() or key_dn_held() or
             key_w_held() or key_s_held() or key_a_held() or key_d_held())

    # ── AUTO PILOT 
    if autopilot:
        gy_now = terrain_height(lander_x, lander_z)
        alt_now = lander_y - gy_now
        dx_t = target_x - lander_x
        dz_t = target_z - lander_z
        dist_h = math.sqrt(dx_t**2 + dz_t**2)
        
        if dist_h > 0.5:
            rocket_heading = (math.degrees(math.atan2(dx_t, dz_t))) % 360.0
        
        if dist_h > 1.0:
            push = min(0.9, dist_h * 0.012)
            nx_t = dx_t / dist_h;  nz_t = dz_t / dist_h
            vel_x += nx_t * push * TH * 6.0
            vel_z += nz_t * push * TH * 6.0
        else:
            vel_x *= 0.88
            vel_z *= 0.88
        
        safe_descent = -min(0.28, 0.06 * math.sqrt(max(alt_now, 0.1)))
        v_err = safe_descent - vel_y
        ap_thrust = max(0.0, min(v_err * 6.0, TU))
        if alt_now > 0.6:
            if hf:
                vel_y += ap_thrust
                fuel = max(0, fuel - FB * (ap_thrust / max(TU,1e-9)) * 1.4)
            elif ho:
                vel_y += ap_thrust * 0.55
                oxygen = max(0, oxygen - 0.10 * (ap_thrust / max(TU,1e-9)) * 1.4)
        
        lander_tilt_z *= 0.88
        lander_tilt_x *= 0.88
        
        wx2, wz2 = get_wind();  vel_x += wx2;  vel_z += wz2
        vel_x *= DR;  vel_z *= DR
        vel_x = max(-MX, min(MX, vel_x));  vel_z = max(-MX, min(MX, vel_z))
        vel_y = max(-MX, min(MX, vel_y))
        lander_x += vel_x;  lander_y += vel_y;  lander_z += vel_z
        gy = terrain_height(lander_x, lander_z)
        if fuel <= 0 and oxygen <= 0 and lander_y > gy + 0.5:
            landing_msg = f"OUT OF PROPELLANT! Score:{score}";  game_over = True
            vel_x = vel_y = vel_z = 0;  move_target();  return
        if lander_y <= gy + 0.5:
            lander_y = gy + 0.5
            speed = math.sqrt(vel_x**2 + vel_y**2 + vel_z**2) * 60
            lv  = get_land_vel_max();  rad = get_target_radius()
            dist_hit = math.sqrt((lander_x-target_x)**2 + (lander_z-target_z)**2)
            on_target = (dist_hit <= rad)
            if on_target and speed <= lv:
                prec = max(0.0, 1.0 - dist_hit/rad);  mult = 1.0 + prec
                pts = int(max(1, int(10*level)) * mult);  score += pts;  level += 1
                landing_msg = f"PERFECT! +{pts}pts (x{mult:.1f}) Speed:{speed:.1f} -> LEVEL {level}!"
            elif on_target:
                landing_msg = f"TOO FAST! Speed:{speed:.1f} (need<={lv:.1f}) Score:{score}"
            else:
                landing_msg = f"CRASHED! {dist_hit:.1f}m from target. Score:{score}"
            move_target();  game_over = True;  vel_x = vel_y = vel_z = 0
        return   
    

    if key_space_held():
        if hf:   vel_y+=TU; fuel=max(0,fuel-FB)
        elif ho: vel_y+=TU*0.55; oxygen=max(0,oxygen-0.10)
     
        dx = dz = 0.0
        if key_w_held(): dx += fwx; dz += fwz
        if key_s_held(): dx -= fwx; dz -= fwz
        if key_d_held(): dx += rtx; dz += rtz
        if key_a_held(): dx -= rtx; dz -= rtz
        dl = math.sqrt(dx*dx + dz*dz)
        if dl > 1e-9:
            dx /= dl; dz /= dl
            vel_x += dx * (TU * 0.60)
            vel_z += dz * (TU * 0.60)
    if key_dn_held():
        if hf:   vel_y-=TU*0.45; fuel=max(0,fuel-FB*0.5)
        elif ho: vel_y-=TU*0.25; oxygen=max(0,oxygen-0.06)

    # ── Horizontal (WASD) 
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


#  RESET

def reset_game():
    global lander_x,lander_y,lander_z,vel_x,vel_y,vel_z,fuel,oxygen
    global game_started,game_over,landing_msg,gp_cam_pitch
    global lander_tilt_z,lander_tilt_x,rocket_heading,gp_cam_yaw,gp_cam_dist
    key_last_seen.clear()
    lander_x=lander_z=0.0; lander_y=terrain_height(0,0)+75.0
    vel_x=vel_y=vel_z=0.0; fuel=oxygen=100.0
    game_started=game_over=False; landing_msg=""
    gp_cam_pitch=22.0; gp_cam_yaw=0.0; gp_cam_dist=45.0
    lander_tilt_z=lander_tilt_x=rocket_heading=0.0
    global autopilot; autopilot=False

def full_reset():
    global score,level
    score=0; level=1; move_target(); reset_game()

#  DISPLAY  — 

def show_screen():
    glClearColor(0.04,0.04,0.08,1.0)
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)

    if current_state in ["MENU","OPTIONS"]:
        draw_interactive_scene()
        _ortho_push(); glDisable(GL_DEPTH_TEST)
        active=main_menu if current_state=="MENU" else options_menu
        for i,opt in enumerate(active): draw_button(500,500-(i*90),opt,i)
        glEnable(GL_DEPTH_TEST); _ortho_pop()

    elif current_state=="TUTORIAL":
        draw_interactive_scene()
        _ortho_push(); glDisable(GL_DEPTH_TEST)
        glColor3f(0.95,0.95,0.95)
        draw_text(50,750,"LUNAR DESCENT TUTORIAL (Use W/S or UP/DOWN to scroll, ESC to go back)",0.7,0.7,0.7)
        y_pos=720
        max_lines=22
        for i in range(tutorial_scroll, min(tutorial_scroll+max_lines, len(tutorial_text))):
            line=tutorial_text[i]
            if line.isupper() and len(line)<40:
                glColor3f(1.0,1.0,0.3)
            elif line.startswith(tuple("0123456789")):
                glColor3f(0.7,1.0,0.7)
            else:
                glColor3f(0.9,0.9,0.9)
            draw_text(70,y_pos,line,*([0.9,0.9,0.9] if not line or len(line)<40 else [0.8,0.8,0.8]))
            y_pos-=20
        scroll_pct=int(100*tutorial_scroll/max(1,len(tutorial_text)-max_lines))
        glColor3f(0.6,0.6,0.6)
        draw_text(950,50,f"[{scroll_pct}%]",0.6,0.6,0.6)
        glEnable(GL_DEPTH_TEST); _ortho_pop()

    elif current_state=="ROCKET_LIST":
        _ortho_push(); glDisable(GL_DEPTH_TEST)
        draw_text(400,650,"SELECT SPACECRAFT",1,1,1)
        for i in range(3): draw_button(500,500-(i*100),rocket_list[i],i)
        draw_button(500,200,"START MISSION",3); draw_button(150,50," BACK ",99)
        if show_alert: draw_text(300,350,alert_message,1,0,0)
        glEnable(GL_DEPTH_TEST); _ortho_pop()

    elif current_state=="ROCKET_VIEWER":
        set_perspective(45,WIN_W/WIN_H,0.1,100.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        glTranslatef(0,0,-25*zoom_level)
        glRotatef(cam_rx,1,0,0); glRotatef(cam_ry,0,1,0)
        glTranslatef(0,-1.5,0)
        if   selected_rocket_index==0: draw_jak_hound()
        elif selected_rocket_index==1: draw_eva_nation()
        elif selected_rocket_index==2: draw_jf17_thunder()
        _ortho_push(); glDisable(GL_DEPTH_TEST)
        draw_text(20,750,f"INSPECTING: {rocket_list[selected_rocket_index]}",1,1,0)
        sel=(selected_rocket_for_game==selected_rocket_index)
        if sel: draw_text(20,720,"[SELECTED]  F: reselect",0,1,0)
        else:   draw_text(20,720,"Press F to select this rocket",0.7,0.7,0.7)
        draw_text(20,690,"ARROWS:ROTATE | N:ZOOM IN | M:ZOOM OUT | ESC:BACK",0.5,0.5,0.5)
        draw_button(150,50," BACK ",99)
        glEnable(GL_DEPTH_TEST); _ortho_pop()

    elif current_state=="GAMEPLAY":
        set_perspective(58,WIN_W/WIN_H,1.0,1800.0)
        hr=math.radians(gp_cam_yaw); pr=math.radians(gp_cam_pitch)
        ecx=lander_x - math.sin(hr)*gp_cam_dist*math.cos(pr)
        ecy=lander_y + gp_cam_dist*math.sin(pr)
        ecz=lander_z - math.cos(hr)*gp_cam_dist*math.cos(pr)
        set_camera(ecx,ecy,ecz, lander_x,lander_y,lander_z)
        draw_space_background()
        draw_terrain()
        draw_target()
        draw_heading_indicator()
        draw_new_target_arrow()
        if not game_over: draw_trajectory()
        glPushMatrix()
        glTranslatef(lander_x,lander_y,lander_z)
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


#  INPUT

def keyboard_listener(key, x, y):
    global current_state,selected_option,zoom_level
    global selected_rocket_index,selected_rocket_for_game
    global rocket_selected,show_alert,alert_message

    k=key.lower() if isinstance(key,bytes) else key

    if k==b'\x1b':
        global tutorial_scroll
        key_last_seen.clear()
        if current_state=="GAMEPLAY":        current_state="MENU";        reset_game()
        elif current_state=="OPTIONS":       current_state="MENU";        selected_option=1
        elif current_state=="ROCKET_LIST":   current_state="OPTIONS";     selected_option=1; show_alert=False
        elif current_state=="ROCKET_VIEWER": current_state="ROCKET_LIST"; selected_option=selected_rocket_index
        elif current_state=="TUTORIAL":      current_state="OPTIONS";     selected_option=0; tutorial_scroll=0
        glutPostRedisplay(); return

    if current_state=="GAMEPLAY":
        if k in (b'w',b's',b'a',b'd'): _key_press(k)   # movement keys
        if k==b' ': _key_press(b'\x00sp')              # SPACE = thrust
        if k==b'r': reset_game()
        if k==b'q': full_reset()
        if k==b'c':              
            global autopilot
            autopilot = not autopilot
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

def special_key_listener(key, x, y):
    global cam_rx,cam_ry,selected_option,gp_cam_pitch,gp_cam_yaw,gp_cam_dist,tutorial_scroll

    if current_state=="GAMEPLAY":
       
        if   key==GLUT_KEY_LEFT:      gp_cam_yaw = (gp_cam_yaw - 4.0) % 360.0
        elif key==GLUT_KEY_RIGHT:     gp_cam_yaw = (gp_cam_yaw + 4.0) % 360.0
        elif key==GLUT_KEY_UP:        gp_cam_pitch = min(80.0, gp_cam_pitch + 2.5)
        elif key==GLUT_KEY_DOWN:      gp_cam_pitch = max(5.0,  gp_cam_pitch - 2.5)
       
        elif key==GLUT_KEY_PAGE_UP:   gp_cam_dist = max(18.0, gp_cam_dist - 2.0)
        elif key==GLUT_KEY_PAGE_DOWN: gp_cam_dist = min(90.0, gp_cam_dist + 2.0)

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

def mouse_listener(button,state,x,y):
    global current_state,selected_option,selected_rocket_index
    global last_click_x,last_click_y,rocket_selected,show_alert,alert_message,tutorial_scroll

    if button==GLUT_LEFT_BUTTON and state==GLUT_DOWN:
        last_click_x,last_click_y=x,y; ly=WIN_H-y
        if current_state=="TUTORIAL":
            if x<=250 and ly<=100: current_state="OPTIONS"; selected_option=0; tutorial_scroll=0
        elif current_state=="ROCKET_LIST":
            for i in range(3):
                if 400<=x<=600 and (500-(i*100)-10)<=ly<=(500-(i*100)+25):
                    selected_rocket_index=i; current_state="ROCKET_VIEWER"
            if 400<=x<=600 and 190<=ly<=225:
                if not rocket_selected: show_alert=True; alert_message="Select a spacecraft first!"
                else: full_reset(); current_state="GAMEPLAY"
            if x<=250 and ly<=100: current_state="OPTIONS"; selected_option=1
        elif current_state=="ROCKET_VIEWER":
            if x<=250 and ly<=100: current_state="ROCKET_LIST"
        else:
            active=main_menu if current_state=="MENU" else options_menu
            for i in range(len(active)):
                if 400<=x<=600 and (500-(i*90)-10)<=ly<=(500-(i*90)+25):
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



def idle():
    global animation_time,planet_rotation_y,frame_count
    frame_count+=1
    animation_time+=0.01
    planet_rotation_y+=0.015
    if current_state=="GAMEPLAY":
        update_physics()        
    glutPostRedisplay()

    
#  MAIN

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(WIN_W,WIN_H)
    glutInitWindowPosition(0,0)
    glutCreateWindow(b"Lunar Descent")
    glutDisplayFunc(show_screen)
    glutKeyboardFunc(keyboard_listener)
    glutSpecialFunc(special_key_listener)
    glutMouseFunc(mouse_listener)
    glutIdleFunc(idle)
    move_target()
    reset_game()
    glutMainLoop()

if __name__=="__main__":
    main()
