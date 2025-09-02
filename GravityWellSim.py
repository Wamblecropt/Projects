# {Heavy sim, be careful while using on lower end machines!}
# ---------------------------------------------------------------------------------------------------------------
# --- This is a gravity well simulator written in python. ---
# --- How it works: ---
'''
Left Mouse Click → Place a gravity well at the mouse position
Right Mouse Click → Spawn a cluster of particles (30 by default)
C → Clear all particles
W → Clear all gravity wells
H → Toggle help overlay (on-screen instructions)
ESC → Quit the program
'''

import json, math, random, time, pathlib
from dataclasses import dataclass
from typing import List, Optional, Tuple
import pygame

# =========================
# Config (tweak to taste)
# =========================
WIDTH, HEIGHT = 1280, 800
RENDER_HZ = 120.0              # target render rate
PHYSICS_HZ = 120.0            # fixed physics step (keeps sim stable); 60 is fine too
G_CONST = 2000.0
SOFTENING2 = 9.0              # gravitational softening^2
PARTICLE_MAX_SPEED = 2400.0
MAX_PARTICLES = 30_000
DEFAULT_PARTICLES = 2_000
WELL_MASS = 8e4
PARTICLE_MASS = 1.0
VSYNC = True
TRAIL_ALPHA_SUB = 14          # lower = longer trails

# Colors
HUD_COLOR = (220, 230, 245)
WELL_COLOR = (2, 2, 2)
BG = (0, 0, 0)

# Utility ---------------

def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v
def lerp(a, b, t): return a + (b - a) * t

# =========================
# Camera with smoothing
# =========================
class Camera:
    def __init__(self):
        self.zoom = 1.0
        self.offset = pygame.Vector2(0, 0)
        self._target_zoom = 1.0
        self._target_offset = pygame.Vector2(0, 0)

    def world_to_screen(self, p: pygame.Vector2) -> pygame.Vector2:
        return (p - self.offset) * self.zoom

    def screen_to_world(self, p: Tuple[float, float]) -> pygame.Vector2:
        return pygame.Vector2(p[0] / self.zoom, p[1] / self.zoom) + self.offset

    def zoom_at(self, factor: float, screen_pos: Tuple[int, int]):
        # cursor-centric zoom with smoothed target
        before = self.screen_to_world(screen_pos)
        self._target_zoom = clamp(self._target_zoom * factor, 0.15, 6.0)
        after = (before - self._target_offset) * (self._target_zoom / self.zoom) + self._target_offset
        # adjust target offset to keep cursor anchored
        self._target_offset += (before - self.screen_to_world(screen_pos))

    def pan(self, delta_screen: pygame.Vector2):
        self._target_offset -= (delta_screen / self.zoom)

    def jump_to(self, pos_world: pygame.Vector2):
        self.offset = pygame.Vector2(pos_world) - pygame.Vector2(WIDTH/2, HEIGHT/2) / self.zoom
        self._target_offset = pygame.Vector2(self.offset)

    def update(self, dt: float):
        # critically-damped like smoothing
        z_smooth = 1 - pow(0.001, dt * 8)
        o_smooth = 1 - pow(0.001, dt * 10)
        self.zoom = lerp(self.zoom, self._target_zoom, z_smooth)
        self.offset.x = lerp(self.offset.x, self._target_offset.x, o_smooth)
        self.offset.y = lerp(self.offset.y, self._target_offset.y, o_smooth)

# =========================
# Data
# =========================
@dataclass
class Well:
    pos: pygame.Vector2
    mass: float = WELL_MASS
    radius: float = 10.0

@dataclass
class Particle:
    pos: pygame.Vector2
    vel: pygame.Vector2
    mass: float = PARTICLE_MASS
    alive: bool = True
    hue: float = 0.6   # for palette variations

# =========================
# Barnes–Hut Quadtree
# =========================
class Quad:
    __slots__ = ("cx", "cy", "hw", "mass", "comx", "comy", "body", "nw", "ne", "sw", "se", "has_children")
    def __init__(self, cx, cy, hw):
        self.cx, self.cy, self.hw = cx, cy, hw
        self.mass = 0.0
        self.comx = 0.0
        self.comy = 0.0
        self.body: Optional[Particle] = None
        self.nw = self.ne = self.sw = self.se = None
        self.has_children = False

    def contains(self, p: Particle):
        return (self.cx - self.hw <= p.pos.x < self.cx + self.hw and
                self.cy - self.hw <= p.pos.y < self.cy + self.hw)

    def _child(self, p: Particle):
        if p.pos.x < self.cx:
            if p.pos.y < self.cy: return "nw"
            else: return "sw"
        else:
            if p.pos.y < self.cy: return "ne"
            else: return "se"

    def subdivide(self):
        h = self.hw / 2
        self.nw = Quad(self.cx - h, self.cy - h, h)
        self.ne = Quad(self.cx + h, self.cy - h, h)
        self.sw = Quad(self.cx - h, self.cy + h, h)
        self.se = Quad(self.cx + h, self.cy + h, h)
        self.has_children = True

    def insert(self, p: Particle):
        if self.hw < 1:  # too small
            # accumulate mass but don't place body to avoid infinite recursion
            self._accumulate(p)
            return
        if self.body is None and not self.has_children:
            self.body = p
            self.mass = p.mass
            self.comx, self.comy = p.pos.x, p.pos.y
            return
        if not self.has_children:
            self.subdivide()
            if self.body is not None:
                getattr(self, self._child(self.body)).insert(self.body)
                self.body = None
        getattr(self, self._child(p)).insert(p)
        self._accumulate(p)

    def _accumulate(self, p: Particle):
        m = self.mass + p.mass
        if m == 0: return
        self.comx = (self.comx * self.mass + p.pos.x * p.mass) / m
        self.comy = (self.comy * self.mass + p.pos.y * p.mass) / m
        self.mass = m

    def force(self, p: Particle, theta: float):
        # returns ax, ay contribution from this node on p
        if self.mass == 0 or (self.body is p):
            return 0.0, 0.0
        dx = self.comx - p.pos.x
        dy = self.comy - p.pos.y
        r2 = dx*dx + dy*dy + SOFTENING2
        # opening criterion
        if not self.has_children:
            # leaf or single body
            inv_r = 1.0 / math.sqrt(r2)
            inv_r3 = inv_r * inv_r * inv_r
            a = G_CONST * self.mass * inv_r3
            return a*dx, a*dy
        s = self.hw * 2
        if s * s / r2 < theta * theta:
            inv_r = 1.0 / math.sqrt(r2)
            inv_r3 = inv_r * inv_r * inv_r
            a = G_CONST * self.mass * inv_r3
            return a*dx, a*dy
        ax = ay = 0.0
        if self.nw: a1, b1 = self.nw.force(p, theta); ax += a1; ay += b1
        if self.ne: a1, b1 = self.ne.force(p, theta); ax += a1; ay += b1
        if self.sw: a1, b1 = self.sw.force(p, theta); ax += a1; ay += b1
        if self.se: a1, b1 = self.se.force(p, theta); ax += a1; ay += b1
        return ax, ay

# =========================
# Simulator
# =========================
class GravitySim:
    def __init__(self):
        self.wells: List[Well] = []
        self.particles: List[Particle] = []
        self.time_scale = 1.0
        self.paused = False
        self.trails = True
        self.show_help = True
        self.show_stats = True
        self.barnes_hut = True
        self.theta = 0.7
        self.seed = 7
        random.seed(self.seed)

    def add_well(self, pos_world: pygame.Vector2, mass=WELL_MASS):
        self.wells.append(Well(pos_world, mass=mass))

    def remove_well_at(self, pos_world: pygame.Vector2, radius_px: float = 20):
        if not self.wells: return
        closest_i, closest_d2 = None, float("inf")
        for i, w in enumerate(self.wells):
            d2 = (w.pos - pos_world).length_squared()
            if d2 < closest_d2:
                closest_i, closest_d2 = i, d2
        if closest_i is not None and closest_d2 <= (radius_px * radius_px):
            self.wells.pop(closest_i)

    def add_particle(self, pos_world: pygame.Vector2, vel_world: pygame.Vector2):
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(Particle(pos=pygame.Vector2(pos_world),
                                           vel=pygame.Vector2(vel_world),
                                           mass=PARTICLE_MASS,
                                           hue=random.random()))

    def clear_all(self):
        self.particles.clear()
        self.wells.clear()

    # Physics ----------------

    def _build_tree(self):
        # Determine bounds (square)
        if not self.particles and not self.wells:
            return None
        xs = [p.pos.x for p in self.particles] + [w.pos.x for w in self.wells]
        ys = [p.pos.y for p in self.particles] + [w.pos.y for w in self.wells]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        cx = (minx + maxx) * 0.5
        cy = (miny + maxy) * 0.5
        half = max(maxx - minx, maxy - miny) * 0.5 + 4.0
        root = Quad(cx, cy, max(half, 64.0))
        # Insert wells as massive bodies (optional, improves performance when many wells)
        for w in self.wells:
            pseudo = Particle(pos=pygame.Vector2(w.pos), vel=pygame.Vector2(), mass=w.mass)
            root.insert(pseudo)
        for p in self.particles:
            root.insert(p)
        return root

    def _forces_direct(self, p: Particle):
        ax = ay = 0.0
        for w in self.wells:
            dx = w.pos.x - p.pos.x
            dy = w.pos.y - p.pos.y
            r2 = dx*dx + dy*dy + SOFTENING2
            inv_r = 1.0 / math.sqrt(r2)
            inv_r3 = inv_r * inv_r * inv_r
            a = G_CONST * w.mass * inv_r3
            ax += a * dx; ay += a * dy
        for q in self.particles:
            if q is p: continue
            dx = q.pos.x - p.pos.x
            dy = q.pos.y - p.pos.y
            r2 = dx*dx + dy*dy + SOFTENING2
            inv_r = 1.0 / math.sqrt(r2)
            inv_r3 = inv_r * inv_r * inv_r
            a = G_CONST * q.mass * inv_r3
            ax += a * dx; ay += a * dy
        return ax, ay

    def step(self, dt: float):
        if not self.particles:
            return
        tree = None
        if self.barnes_hut and (len(self.particles) > 400):
            tree = self._build_tree()

        # Integrate (leapfrog / velocity Verlet)
        for p in self.particles:
            if not p.alive: continue
            ax = ay = 0.0
            if tree:
                axt, ayt = tree.force(p, self.theta)
                ax += axt; ay += ayt
            else:
                # wells
                for w in self.wells:
                    dx = w.pos.x - p.pos.x; dy = w.pos.y - p.pos.y
                    r2 = dx*dx + dy*dy + SOFTENING2
                    inv_r = 1.0 / math.sqrt(r2); inv_r3 = inv_r * inv_r * inv_r
                    a = G_CONST * w.mass * inv_r3
                    ax += a*dx; ay += a*dy
                # particle-particle only if small N
                if len(self.particles) <= 700:
                    for q in self.particles:
                        if q is p: continue
                        dx = q.pos.x - p.pos.x; dy = q.pos.y - p.pos.y
                        r2 = dx*dx + dy*dy + SOFTENING2
                        inv_r = 1.0 / math.sqrt(r2); inv_r3 = inv_r * inv_r * inv_r
                        a = G_CONST * q.mass * inv_r3
                        ax += a*dx; ay += a*dy

            p.vel.x += ax * dt; p.vel.y += ay * dt
            sp = p.vel.length()
            if sp > PARTICLE_MAX_SPEED:
                p.vel.scale_to_length(PARTICLE_MAX_SPEED)
            p.pos += p.vel * dt

# =========================
# Fancy spawners
# =========================
def spawn_ring(sim: GravitySim, center: pygame.Vector2, n=1000, radius=280, speed=220):
    for i in range(n):
        ang = (i / n) * math.tau
        pos = center + pygame.Vector2(radius * math.cos(ang), radius * math.sin(ang))
        tangent = pygame.Vector2(-math.sin(ang), math.cos(ang))
        vel = tangent * (speed * (0.85 + 0.3 * random.random()))
        sim.add_particle(pos, vel)

def spawn_spiral(sim: GravitySim, center: pygame.Vector2, arms=3, per_arm=500, base_speed=210):
    for a in range(arms):
        base_ang = a * (math.tau / arms)
        for i in range(per_arm):
            r = 6 + i * 2.6
            ang = base_ang + i * 0.07
            pos = center + pygame.Vector2(r * math.cos(ang), r * math.sin(ang))
            tangent = pygame.Vector2(-math.sin(ang), math.cos(ang))
            vel = tangent * (base_speed * (0.8 + 0.4 * random.random()))
            sim.add_particle(pos, vel)

def spawn_galaxy(sim: GravitySim, center: pygame.Vector2, arms=2, per_arm=2500, dispersion=22, speed=230):
    for a in range(arms):
        base_ang = a * (math.tau / arms)
        for i in range(per_arm):
            r = 10 + i * 1.2
            jitter = pygame.Vector2(random.uniform(-dispersion, dispersion),
                                    random.uniform(-dispersion, dispersion))
            ang = base_ang + i * 0.045 + random.uniform(-0.05, 0.05)
            pos = center + pygame.Vector2(r * math.cos(ang), r * math.sin(ang)) + jitter
            tangent = pygame.Vector2(-math.sin(ang), math.cos(ang))
            vel = tangent * (speed * (0.85 + 0.3 * random.random()))
            sim.add_particle(pos, vel)

def spawn_cloud(sim: GravitySim, center: pygame.Vector2, count=3000, spread=(420, 300), max_speed=260):
    for _ in range(count):
        pos = center + pygame.Vector2(random.uniform(-spread[0], spread[0]),
                                      random.uniform(-spread[1], spread[1]))
        vel = pygame.Vector2(random.uniform(-max_speed, max_speed),
                             random.uniform(-max_speed, max_speed)) * 0.35
        sim.add_particle(pos, vel)

# =========================
# Rendering
# =========================
def speed_color(speed: float, palette: int = 0):
    # palette 0: cool -> hot; palette 1: neon cyan -> magenta -> white
    t = clamp(speed / 800.0, 0.0, 1.0)
    if palette == 0:
        # dark blue -> cyan -> yellow -> white
        if t < 0.5:
            u = t / 0.5
            r, g, b = int(30*(1-u) + 0*u), int(70*(1-u) + 255*u), int(160*(1-u) + 255*u)
        else:
            u = (t-0.5)/0.5
            r, g, b = int(0*(1-u) + 255*u), int(255*(1-u) + 255*u), int(255*(1-u) + 255*u)
        return (r, g, b)
    else:
        # cyan -> magenta -> white
        if t < 0.5:
            u = t/0.5
            r = int(0*(1-u) + 255*u); g = int(255*(1-u) + 0*u); b = 255
        else:
            u = (t-0.5)/0.5
            r = 255; g = int(0*(1-u) + 255*u); b = 255
        return (r, g, b)

def draw_well_glow(surf: pygame.Surface, cam: Camera, w: Well):
    c = cam.world_to_screen(w.pos)
    pygame.draw.circle(surf, WELL_COLOR, (int(c.x), int(c.y)), max(2, int(w.radius * cam.zoom)))
    max_r = int(110 * cam.zoom)
    for r in (max_r, int(max_r*0.55), int(max_r*0.25)):
        alpha = max(12, int(130 * (r / max_r) ** 1.15))
        glow = pygame.Surface((r*2+1, r*2+1), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*WELL_COLOR, alpha), (r, r), r)
        surf.blit(glow, (c.x - r, c.y - r), special_flags=pygame.BLEND_PREMULTIPLIED)

def draw(sim: GravitySim, screen: pygame.Surface, trail_layer: pygame.Surface,
         cam: Camera, font, small, palette_idx, launch_start, launch_end,
         fps, steps_last, dt):
    # fade trails or clear
    if sim.trails:
        trail_layer.fill((0, 0, 0, TRAIL_ALPHA_SUB), special_flags=pygame.BLEND_RGBA_SUB)
        canvas = trail_layer
    else:
        trail_layer.fill((0, 0, 0, 255))
        canvas = trail_layer

    # particles
    put = pygame.Surface((2, 2), pygame.SRCALPHA); put.fill((255,255,255,255))
    for p in sim.particles:
        sp = cam.world_to_screen(p.pos)
        if -2 <= sp.x <= WIDTH+2 and -2 <= sp.y <= HEIGHT+2:
            col = speed_color(p.vel.length(), palette_idx)
            put.fill((*col, 255))
            canvas.blit(put, (sp.x, sp.y))

    # compose trails
    screen.blit(trail_layer, (0, 0))

    # wells & effects
    for w in sim.wells:
        draw_well_glow(screen, cam, w)

    # launch vector preview
    if launch_start and launch_end:
        pygame.draw.line(screen, (130, 140, 170), launch_start, launch_end, 2)
        pygame.draw.circle(screen, (130,140,170), launch_start, 4)

    # HUD
    if sim.show_stats or sim.show_help:
        lines = []
        if sim.show_stats:
            lines += [
                f"Particles: {len(sim.particles):,} / {MAX_PARTICLES:,}    Wells: {len(sim.wells)}",
                f"Render: {fps:5.1f} fps  Physics: {PHYSICS_HZ:.0f} Hz  Steps/frame: {steps_last}",
                f"Time x{sim.time_scale:.2f}    Trails: {'on' if sim.trails else 'off'}",
                f"Barnes–Hut: {'on' if sim.barnes_hut else 'off'}  θ={sim.theta:.2f}",
            ]
        if sim.show_help:
            lines += [
                "Mouse: Left-drag launch | Right-click add well | Shift+Right remove | Wheel zoom | Middle/Space+drag pan",
                "Keys: P/Space pause  T trails  B Barnes–Hut  -/= θ  [ ] time  R reset  H help  F stats  C palette  F12 screenshot",
                "      1 ring  2 spiral  3 cloud  G galaxy  O orbit-at-cursor  S save  L load  K reseed",
            ]
        y = 10
        for line in lines:
            text = font.render(line, True, HUD_COLOR); screen.blit(text, (10, y)); y += text.get_height() + 2

# =========================
# Save/Load
# =========================
def save_sim(sim: GravitySim, path: pathlib.Path):
    data = {
        "wells": [{"x": float(w.pos.x), "y": float(w.pos.y), "mass": float(w.mass)} for w in sim.wells],
        "particles": [{"x": float(p.pos.x), "y": float(p.pos.y),
                       "vx": float(p.vel.x), "vy": float(p.vel.y)} for p in sim.particles],
        "time_scale": sim.time_scale, "theta": sim.theta, "barnes_hut": sim.barnes_hut,
    }
    path.write_text(json.dumps(data))

def load_sim(sim: GravitySim, path: pathlib.Path):
    if not path.exists(): return False
    data = json.loads(path.read_text())
    sim.clear_all()
    for w in data.get("wells", []):
        sim.add_well(pygame.Vector2(w["x"], w["y"]), mass=w.get("mass", WELL_MASS))
    for q in data.get("particles", []):
        sim.add_particle(pygame.Vector2(q["x"], q["y"]), pygame.Vector2(q["vx"], q["vy"]))
    sim.time_scale = float(data.get("time_scale", 1.0))
    sim.theta = float(data.get("theta", 0.7))
    sim.barnes_hut = bool(data.get("barnes_hut", True))
    return True

# =========================
# Main
# =========================
def main():
    pygame.init()
    flags = pygame.SCALED | pygame.DOUBLEBUF
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags, vsync=1 if VSYNC else 0)
    pygame.display.set_caption("Gravity Well Sim")

    font = pygame.font.SysFont("consolas", 16)
    small = pygame.font.SysFont("consolas", 14)

    clock = pygame.time.Clock()
    trail_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); trail_layer.fill((0,0,0,255))

    cam = Camera()
    sim = GravitySim()
    palette_idx = 0

    # initial setup: twin wells + ring
    center = cam.screen_to_world((WIDTH//2, HEIGHT//2))
    sim.add_well(center + pygame.Vector2(-200, 0))
    sim.add_well(center + pygame.Vector2(200, 0))
    spawn_ring(sim, center, n=DEFAULT_PARTICLES, radius=280, speed=220)

    running = True
    dragging_left = False
    dragging_mid = False
    pan_start = pygame.Vector2(0, 0)
    cam_start = pygame.Vector2(0, 0)
    launch_start = None
    launch_end = None

    fixed_dt = 1.0 / PHYSICS_HZ
    accumulator = 0.0
    steps_last = 0
    fps = 0.0

    screenshot_dir = pathlib.Path("./screenshots"); screenshot_dir.mkdir(exist_ok=True)
    state_path = pathlib.Path("./gravity_state.json")

    while running:
        dt_real = clock.tick(RENDER_HZ) / 1000.0
        fps = 1.0 / dt_real if dt_real > 0 else 0.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    dragging_left = True
                    launch_start = event.pos; launch_end = event.pos
                elif event.button == 2:
                    dragging_mid = True
                    pan_start = pygame.Vector2(event.pos); cam_start = pygame.Vector2(cam._target_offset)
                elif event.button == 3:
                    mods = pygame.key.get_mods()
                    pos_world = cam.screen_to_world(event.pos)
                    if mods & pygame.KMOD_SHIFT: sim.remove_well_at(pos_world)
                    else: sim.add_well(pos_world)
                elif event.button == 4:
                    cam.zoom_at(1.1, event.pos)
                elif event.button == 5:
                    cam.zoom_at(1/1.1, event.pos)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and dragging_left:
                    dragging_left = False
                    if launch_start and launch_end:
                        p0 = cam.screen_to_world(launch_start)
                        p1 = cam.screen_to_world(launch_end)
                        v = (p1 - p0) * 2.0
                        sim.add_particle(p0, v)
                    launch_start = None; launch_end = None
                elif event.button == 2:
                    dragging_mid = False

            elif event.type == pygame.MOUSEMOTION:
                if dragging_left:
                    launch_end = event.pos
                keys = pygame.key.get_pressed()
                if dragging_mid or keys[pygame.K_SPACE]:
                    cam._target_offset = cam_start - ( (pygame.Vector2(event.pos) - pan_start) / cam.zoom )

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_p, pygame.K_SPACE): sim.paused = not sim.paused
                elif event.key == pygame.K_t: sim.trails = not sim.trails
                elif event.key == pygame.K_f: sim.show_stats = not sim.show_stats
                elif event.key == pygame.K_h: sim.show_help = not sim.show_help
                elif event.key == pygame.K_c: palette_idx = (palette_idx + 1) % 2
                elif event.key == pygame.K_b: sim.barnes_hut = not sim.barnes_hut
                elif event.key == pygame.K_MINUS: sim.theta = clamp(sim.theta - 0.05, 0.3, 1.2)
                elif event.key == pygame.K_EQUALS: sim.theta = clamp(sim.theta + 0.05, 0.3, 1.2)
                elif event.key == pygame.K_LEFTBRACKET: sim.time_scale = max(0.05, sim.time_scale * 0.8)
                elif event.key == pygame.K_RIGHTBRACKET: sim.time_scale = min(6.0, sim.time_scale * 1.25)
                elif event.key == pygame.K_r:
                    sim.clear_all(); cam = Camera()
                    center = cam.screen_to_world((WIDTH//2, HEIGHT//2))
                    sim.add_well(center + pygame.Vector2(-220, 0))
                    sim.add_well(center + pygame.Vector2(220, 0))
                    spawn_ring(sim, center, n=DEFAULT_PARTICLES, radius=300, speed=220)
                elif event.key == pygame.K_1:
                    center = cam.screen_to_world((WIDTH//2, HEIGHT//2)); spawn_ring(sim, center, n=2000, radius=300, speed=220)
                elif event.key == pygame.K_2:
                    center = cam.screen_to_world((WIDTH//2, HEIGHT//2)); spawn_spiral(sim, center, arms=3, per_arm=600, base_speed=210)
                elif event.key == pygame.K_3:
                    center = cam.screen_to_world((WIDTH//2, HEIGHT//2)); spawn_cloud(sim, center, count=4000, spread=(520,360))
                elif event.key == pygame.K_g:
                    center = cam.screen_to_world((WIDTH//2, HEIGHT//2)); spawn_galaxy(sim, center, arms=2, per_arm=2500)
                elif event.key == pygame.K_o:
                    # quick orbit: add well at cursor and a ring around it
                    pos = cam.screen_to_world(pygame.mouse.get_pos())
                    sim.add_well(pos)
                    spawn_ring(sim, pos, n=1200, radius=240, speed=220)
                elif event.key == pygame.K_k:
                    sim.seed = (sim.seed + 1) & 0xffffffff; random.seed(sim.seed)
                elif event.key == pygame.K_s:
                    save_sim(sim, state_path)
                elif event.key == pygame.K_l:
                    load_sim(sim, state_path)
                elif event.key == pygame.K_F12:
                    ts = int(time.time())
                    path = screenshot_dir / f"gravity_{ts}.png"
                    pygame.image.save(screen, str(path))
                    print(f"Saved screenshot to {path.resolve()}")

        # physics (fixed step w/ accumulator)
        if not sim.paused:
            accumulator += dt_real * sim.time_scale
            steps = 0
            max_steps = int(0.25 / fixed_dt)
            while accumulator >= fixed_dt and steps < max_steps:
                sim.step(fixed_dt)
                accumulator -= fixed_dt; steps += 1
            steps_last = steps

        cam.update(dt_real)

        # render
        screen.fill(BG)
        draw(sim, screen, trail_layer, cam, font, small, palette_idx, launch_start, launch_end, fps, steps_last, dt_real)
        pygame.display.flip()

    pygame.quit()

# -------------
if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------------------------------------------