# Lunar Descent — A Moon Landing Simulator

A physics-driven 3D moon landing simulator built entirely with Python and OpenGL. Pilot a spacecraft, manage limited fuel and oxygen, and land precisely on a target pad across progressively harder levels.

Inspired by the **Artemis II lunar flyby mission (April 2026)**.

---

## Team

- **Farhana Tasnim Eva**
- **S K Tasrian Munstasir**
- **Jaky Ahmed Chowdhury**

---

## Overview

Lunar Descent puts you in control of a spacecraft descending toward a procedurally generated lunar surface. The objective is to land inside the designated target zone at a safe speed before your fuel runs out. Each level raises the stakes — gravity increases, the target pad shrinks, wind kicks in, and your margins for error get tighter.

The project was developed in two versions:
- **Restricted version** — built within a limited set of permitted OpenGL functions
- **Updated version** — full OpenGL feature set with lighting, smooth normals, particle effects, and display list optimization

---

## Features

**Gameplay**
- Land on a procedurally generated lunar surface with mountains and craters
- Dual resource system: primary fuel and backup oxygen
- Autopilot mode with real-time descent calculation
- Real-time trajectory prediction line
- Progressive difficulty across levels (gravity, wind, pad size, speed limit)
- Three rockets to choose from: JakHound F-22, EvaNation F-15, JF17 Thunder

**Physics**
- Gravity, atmospheric drag, thrust, and wind forces
- Fuel regeneration when idle on oxygen backup
- Tilt simulation based on lateral movement
- Delta-time based updates for frame-rate independence

**Graphics (Updated Version)**
- OpenGL lighting with directional sun and fill light
- Smooth per-vertex terrain normals compiled into display lists
- Additive-blended exhaust and retro-thrust flames
- Particle system for engine exhaust and landing impact debris
- Screen shake on crash or hard landing
- Glow rings and animated beacon on the landing target
- Alpha-blended trajectory line color-coded by landing speed

**HUD & Navigation**
- Live readouts: fuel, oxygen, speed, altitude, velocity components, distance to target
- Graphical bars for fuel, oxygen, and speed
- Minimap with terrain overview, target marker, and heading arrow
- Active key indicator during flight

---

## Controls

| Input | Action |
|---|---|
| SPACE | Main thrust (burns fuel, falls back to oxygen) |
| DOWN ARROW | Retro-thrust (slows descent) |
| W / A / S / D | Strafe forward / left / backward / right |
| LEFT / RIGHT ARROWS | Rotate camera around lander |
| UP / DOWN ARROWS | Adjust camera pitch |
| PAGE UP / PAGE DOWN | Zoom camera in / out |
| C | Toggle autopilot |
| R | Retry (keep score) |
| Q | Full reset |
| ESC | Return to menu |

Diagonal movement works — combine WASD keys freely. All keys can be held simultaneously.

---

## Installation

**Requirements**

- Python 3.8 or higher
- PyOpenGL
- PyOpenGL-accelerate (recommended)
- freeglut (system library)

**Install dependencies**

```bash
pip install PyOpenGL PyOpenGL_accelerate
```

On Linux, also install freeglut:

```bash
sudo apt install freeglut3-dev
```

On Windows, freeglut is typically bundled with PyOpenGL. On macOS:

```bash
brew install freeglut
```

**Run the game**

```bash
python lunar_descent.py
```

---

## How to Play

1. Launch the game and select **Start Game** from the main menu
2. Go to **Options > Check Rocket** to inspect and select your spacecraft
3. Press **Start Mission** to begin
4. Hold **SPACE** to lift off
5. Navigate toward the orange target rings visible on the terrain and minimap
6. Reduce speed as you approach and land gently inside the rings
7. A **PERFECT** landing requires: landing inside the pad AND speed below the level limit
8. Each perfect landing earns points, advances the level, and generates a new target

**Scoring**

```
Base Points  =  10 x Current Level
Precision Multiplier  =  1.0x (pad edge)  to  2.0x (pad center)
Final Score  =  Base x Multiplier
```

---

## Project Structure

```
lunar_descent/
├── lunar_descent.py          # Restricted version (original GL functions only)
├── lunar_descent_updated.py  # Updated version (full GL feature set)
└── README.md
```

---

## Difficulty Progression

| Level | Change |
|---|---|
| 1 | Default gravity, large pad, generous speed limit |
| 2-3 | Gravity increases, pad shrinks, tighter speed cap |
| 4+ | Wind forces introduced, further gravity and pad reduction |
| 10+ | Near-maximum difficulty — minimal pad, high gravity, strong wind |

---

## Inspiration

This project was inspired by **NASA's Artemis II mission**, the first crewed lunar flyby since Apollo 17, which conducted its lunar flyby in April 2026. The simulator captures the challenge of precision orbital maneuvering and controlled descent that real mission planners and astronauts face.

---

## License

This project was developed as an academic submission. All code is original work by the listed team members.
