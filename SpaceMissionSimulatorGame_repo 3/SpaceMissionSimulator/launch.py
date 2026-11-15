"""Launch pad countdown and the atmospheric ascent sequence."""
import math
import random

import pygame

import art
import physics
import ui
from scene import Scene, MissionControl
from settings import *


class Particle:
    def __init__(self, x, y, vx, vy, life, col, size=2):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.col = col
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.98
        self.life -= dt

    def draw(self, s):
        f = max(0.0, self.life / self.max)
        c = tuple(int(v * (0.4 + 0.6 * f)) for v in self.col)
        sz = max(1, int(self.size * (2 - f)))
        pygame.draw.rect(s, c, (int(self.x), int(self.y), sz, sz))


class LaunchPadScene(Scene):
    music = None

    def __init__(self, game):
        super().__init__(game)
        self.ms = game.mission
        self.stack = art.draw_stack(self.ms.design.c)
        self.t = 0.0
        self.state = "ready"
        self.count = 5
        self.ct = 0.0
        self.y_off = 0.0
        self.vel = 0.0
        self.particles = []
        self.shake = 0
        self.boom_t = None
        self.mc = MissionControl(game, (4, 4, 300, 62))
        self.buttons = [ui.Button((330, 230, 140, 30), "LAUNCH!", self.begin, color=RED, size=24,
                                  sound="select", key=pygame.K_SPACE)]
        self.mc.tip("launchpad", [
            "All systems are GO. Press the big red LAUNCH button to start the countdown!",
        ], force=bool(self.ms.level.get("tutorial")))

    def enter(self):
        self.audio.stop_music(500)

    def begin(self):
        if self.state == "ready":
            self.state = "countdown"
            self.buttons = []
            self.mc.box.clear()
            self.audio.play("beep")

    def handle(self, e):
        if self.mc.handle(e):
            return True
        return super().handle(e)

    def update(self, dt):
        self.t += dt
        self.mc.update(dt)
        ground = 230
        cx = 240
        if self.state == "countdown":
            self.ct += dt
            if self.ct >= 0.8:
                self.ct = 0
                self.count -= 1
                if self.count > 0:
                    self.audio.play("beep")
                else:
                    self.audio.play("go")
                    self.audio.play("launch")
                    self.state = "ignition"
                    self.ct = 0
        elif self.state in ("ignition", "liftoff", "stuck"):
            self.ct += dt
            self.shake = 1 if int(self.t * 30) % 2 else -1
            bottom = ground - 4 + self.y_off
            for _ in range(6):
                self.particles.append(Particle(cx + random.uniform(-8, 8), bottom,
                                               random.uniform(-10, 10), random.uniform(30, 80),
                                               random.uniform(0.15, 0.35),
                                               random.choice([YELLOW, ORANGE, WHITE, RED]), 2))
            if self.y_off > -40:
                for _ in range(3):
                    self.particles.append(Particle(cx + random.uniform(-6, 6), ground - 2,
                                                   random.choice([-1, 1]) * random.uniform(30, 90),
                                                   random.uniform(-15, 0), random.uniform(1.0, 2.0),
                                                   random.choice([(200, 200, 200), (160, 160, 170)]), 3))
            if self.state == "ignition" and self.ct > 1.2:
                if self.ms.a["twr"] < physics.MIN_TWR:
                    self.state = "stuck"
                    self.ct = 0
                    self.mc.say("Thrust is too low! The rocket can't lift its own weight!")
                else:
                    self.state = "liftoff"
            if self.state == "stuck" and self.ct > 2.5:
                self.boom()
            if self.state == "liftoff":
                acc = 25 * (self.ms.a["twr"] - 0.9)
                self.vel += acc * dt
                self.y_off -= self.vel * dt
                if self.y_off < -320:
                    self.go_ascent()
        elif self.state == "boom":
            self.boom_t += dt
            if self.boom_t > 2.2:
                from endings import GameOver
                self.ms.fail("Launch failure: thrust-to-weight ratio %.2f - it must be above 1.15 to climb. Use stronger engines "
                             "or a lighter design." % self.ms.a["twr"])
                self.game.switch(GameOver(self.game))
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

    def boom(self):
        self.state = "boom"
        self.boom_t = 0.0
        self.audio.play("explosion")

    def go_ascent(self):
        self.audio.stop("launch")
        self.game.switch(AscentScene(self.game))

    SITE_LOOK = {   # sky top, sky bottom, ground, ground speckle
        "earth": ((60, 110, 190), (120, 160, 210), (60, 70, 56), (80, 92, 70)),
        "moon": ((6, 6, 16), (10, 10, 24), (130, 130, 140), (100, 100, 110)),
        "mars": ((150, 100, 80), (200, 140, 110), (150, 70, 40), (120, 55, 30)),
        "asteroid": ((6, 6, 16), (10, 10, 24), (90, 80, 70), (70, 60, 52)),
    }

    def draw(self, s):
        site = self.ms.level["game"].get("launch", "earth")
        sky_top, sky_bot, gcol, speck = self.SITE_LOOK.get(site, self.SITE_LOOK["earth"])
        sky_shift = min(1.0, -self.y_off / 320)
        top = tuple(int(a + (b - a) * sky_shift) for a, b in zip(sky_top, (10, 10, 40)))
        for i in range(0, H, 2):
            f = i / H
            c = tuple(int(top[j] * (1 - f) + sky_bot[j] * f * (1 - sky_shift)) for j in range(3))
            pygame.draw.rect(s, c, (0, i, W, 2))
        if site in ("moon", "asteroid"):
            for i in range(40):
                s.set_at(((i * 97) % W, (i * 41) % 200), (200, 200, 220))
        ground = 230
        pygame.draw.rect(s, gcol, (0, ground, W, H - ground))
        pygame.draw.rect(s, (100, 100, 106), (170, ground - 4, 140, 4))
        for x in range(0, W, 9):
            s.set_at((x, ground + 8 + (x % 3)), speck)
        if site == "earth":   # ocean strip (Cape Canaveral!)
            pygame.draw.rect(s, (40, 90, 160), (380, ground + 2, 100, 6))
        elif site == "moon":
            s.blit(art.planet("earth", 12), (380, 30))
        stack_h = self.stack.get_height()
        ch = max(60, stack_h + 6)
        s.blit(art.crane(ch), (262, ground - 4 - ch))
        if self.state in ("ready", "countdown"):
            for yy in range(ground - 4 - ch + 10, ground - 10, 26):
                pygame.draw.rect(s, (210, 40, 40), (252, yy, 12, 2))
        dx = self.shake if self.state in ("ignition", "stuck", "liftoff") and self.y_off > -60 else 0
        if self.state != "boom":
            s.blit(self.stack, (240 - 32 + dx, ground - 4 - stack_h + int(self.y_off)))
        for p in self.particles:
            p.draw(s)
        if self.state == "boom":
            art.explosion(s, 240, ground - stack_h // 2, min(1.0, self.boom_t / 1.5))
        if self.state == "countdown":
            ui.text(s, str(self.count), (W // 2, 60), YELLOW, 24, center=True, scale=3)
        elif self.state in ("ignition", "liftoff") and self.ct < 1.5:
            ui.text(s, "IGNITION!" if self.state == "ignition" else "LIFTOFF!", (W // 2, 60), YELLOW, 24,
                    center=True, scale=2)
        pad = {"earth": "LAUNCH COMPLEX 39", "moon": "LUNAR LAUNCH PAD", "mars": "MARS BASE PAD",
               "asteroid": "BENNU SURFACE"}.get(site, "LAUNCH PAD")
        ui.text(s, "%s MISSION - %s" % (self.ms.level["name"].upper(), pad), (W - 6, 6), WHITE, 14, right=True)
        self.draw_buttons(s, 1 / 60)
        self.mc.draw(s)


LAYERS = [  # (name, top altitude km, color)
    ("TROPOSPHERE", 12, (90, 150, 230)),
    ("STRATOSPHERE", 50, (70, 120, 210)),
    ("MESOSPHERE", 85, (54, 90, 180)),
    ("THERMOSPHERE", 600, (40, 60, 140)),
    ("EXOSPHERE", 10000, (26, 34, 90)),
]
ALT_KM = [0, 12, 50, 85, 600, 10000]
ALT_PX = [0, 22, 52, 82, 132, 172]

# Custom background (images/atmosphere.png, 320x180 drawn at 1.5x). Measured from the
# picture: Earth's centre and radius, and the pixel heights of the layer boundaries
# (troposphere = Earth glow + 1st band, stratosphere = 2nd, mesosphere = 3rd,
# thermosphere = 4th+5th, exosphere = 6th+7th band).
BG_FILE = "atmosphere.png"
BG_CENTRE = (240, 280.5)
BG_EARTH_R = 67.5
BG_ALT_PX = [0, 24, 39, 58.5, 99, 144]


def alt_to_px(h, table=None):
    table = table or ALT_PX
    for i in range(len(ALT_KM) - 1):
        if h <= ALT_KM[i + 1]:
            f = (h - ALT_KM[i]) / (ALT_KM[i + 1] - ALT_KM[i])
            return table[i] + f * (table[i + 1] - table[i])
    return table[-1]


def air_temp(h):
    if h < 11:
        return 15 - 6.5 * h
    if h < 20:
        return -56
    if h < 50:
        return -56 + (h - 20) * 1.8
    if h < 85:
        return -2 - (h - 50) * 2.4
    return min(1500, -86 + (h - 85) * 8)


def layer_name(h):
    for name, top, _ in LAYERS:
        if h <= top:
            return name
    return "SPACE"


class AscentScene(Scene):
    """Earth with labelled atmosphere layers, a red dot following the trajectory."""
    DURATION = 16.0

    def __init__(self, game):
        super().__init__(game)
        self.ms = game.mission
        a = self.ms.a
        self.t = 0.0
        self.trail = []
        self.msgs = []
        self.checks_done = set()
        self.boom_t = None
        self.fail_reason = None
        self.done_t = None
        self.R = 640
        self.cx, self.cy = 240, 250 + self.R
        self.px = ALT_PX
        self.arc = (-0.30, 0.80)          # start angle, sweep (radians)
        self.bg = None
        self.site = self.ms.level["game"].get("launch", "earth")
        src = art.custom_image(BG_FILE) if self.site == "earth" else None
        if self.site != "earth":
            self.R = 400
            self.cx, self.cy = 240, 250 + self.R
        if src is not None:
            self.bg = pygame.transform.scale(src, (W, H))
            self.cx, self.cy = BG_CENTRE
            self.R = BG_EARTH_R
            self.px = BG_ALT_PX
            self.arc = (0.22, -0.78)      # climb up and to the left, away from the telemetry
        self.mc = MissionControl(game, (4, 4, 260, 62))
        self.mc.tip("ascent", [
            "This is your rocket's path through Earth's atmosphere. The red dot is YOU.",
            "Watch altitude, speed and temperature on the right. Max-Q (biggest air stress) and heating are the dangerous parts!",
        ], force=bool(self.ms.level.get("tutorial")))
        self.audio.play("launch")

    def alt(self, f):
        if f < 0.75:
            return 220 * (f / 0.75) ** 1.7
        return 220 + (f - 0.75) / 0.25 * 600

    def vel(self, f):
        osp = self.ms.a["orbit_speed"]
        if f < 0.75:
            return osp * (f / 0.75) ** 1.4
        return osp + (min(self.ms.a["max_vel"], osp + 4.7) - osp) * (f - 0.75) / 0.25

    def pos(self, f):
        ang = self.arc[0] + self.arc[1] * f
        r = self.R + alt_to_px(self.alt(f), self.px)
        return self.cx + r * math.sin(ang), self.cy - r * math.cos(ang)

    def say(self, m, col=WHITE):
        self.msgs.append((m, col))
        self.msgs = self.msgs[-5:]

    def explode(self, reason):
        self.fail_reason = reason
        self.boom_t = 0.0
        self.audio.stop("launch")
        self.audio.play("explosion")

    def check(self, key, f):
        a = self.ms.a
        if key in self.checks_done or f < {"maxq": 0.16, "heat": 0.32, "sep": 0.48, "orbit": 0.72,
                                            "tli": 0.86}[key]:
            return
        self.checks_done.add(key)
        if key == "maxq":
            if a["strength"] < a["maxq_need"]:
                self.explode("Structural failure at Max-Q: strength %d but this rocket needed %d. "
                             "Use stronger materials or less violent thrust." % (a["strength"], a["maxq_need"]))
            else:
                if a["maxq_need"] <= 0:
                    self.say("No air here - no Max-Q stress at all!", GREEN)
                else:
                    self.say("MAX-Q passed. Structure holding (%d/%d)" % (a["strength"], a["maxq_need"]), GREEN)
        elif key == "heat":
            if a["heat"] < a["heat_need"]:
                self.explode("Burned up during ascent! Heat resistance %d is below the %d needed. "
                             "Too much aluminium / weak shield?" % (a["heat"], a["heat_need"]))
            else:
                if a["heat_need"] <= 0:
                    self.say("No atmosphere - no ascent heating!", GREEN)
                else:
                    self.say("Peak heating survived (heat rating %d)" % a["heat"], GREEN)
        elif key == "sep":
            self.say("Stage 1 separation. Stage 2 ignition!", YELLOW)
            self.audio.play("whoosh")
        elif key == "orbit":
            if not a["reach_orbit"]:
                why = "the spacecraft engine can't help in the atmosphere" if not self.ms.eng["high_thrust"] \
                    else "not enough delta-v"
                self.explode("Failed to reach orbit (%s). Needed %.1f km/s, the launch vehicle gave %.1f."
                             % (why, a["orbit_need"] / 1000, a["lv_dv"] / 1000))
            else:
                if a["orbit_deficit"] > 0:
                    self.say("Spacecraft engine burns to finish orbit insertion", ORANGE)
                self.say("ORBIT ACHIEVED: %.1f km/s" % a["orbit_speed"], GREEN)
        elif key == "tli":
            if a["max_vel"] < a["escape_need"]:
                self.explode("Stuck in orbit: max velocity %.1f km/s is below the escape velocity "
                             "of %s (%.1f km/s)." % (a["max_vel"], a["site"], a["escape_need"]))
            else:
                self.say("Escape burn! Max velocity %.1f km/s > %.1f escape" % (a["max_vel"], a["escape_need"]),
                         GREEN)

    def handle(self, e):
        return self.mc.handle(e)

    def update(self, dt):
        self.mc.update(dt)
        if self.boom_t is not None:
            self.boom_t += dt
            if self.boom_t > 2.5:
                from endings import GameOver
                self.ms.fail(self.fail_reason)
                self.game.switch(GameOver(self.game))
            return
        if self.mc.active and self.t < 0.5:
            return  # hold on the pad while Mission Control explains
        self.t += dt
        f = min(1.0, self.t / self.DURATION)
        for k in ("maxq", "heat", "sep", "orbit", "tli"):
            self.check(k, f)
            if self.boom_t is not None:
                return
        x, y = self.pos(f)
        if not self.trail or abs(self.trail[-1][0] - x) + abs(self.trail[-1][1] - y) > 2:
            self.trail.append((x, y))
        if f >= 1.0:
            if self.done_t is None:
                self.done_t = 0.0
                self.audio.stop("launch")
                self.audio.play("success")
            self.done_t += dt
            if self.done_t > 1.5:
                self.ms.after_launch()
                from mission import MissionScene
                self.game.switch(MissionScene(self.game), loading=True, label="ENTERING DEEP SPACE")

    def draw_custom_bg(self, s):
        """Your atmosphere picture, with a label key on the right pointing into each layer."""
        s.blit(self.bg, (0, 0))
        cx, cy, R = self.cx, self.cy, self.R
        lo = 0
        rows = len(LAYERS)
        for i, (name, top, col) in enumerate(LAYERS):
            r_mid = R + (alt_to_px(lo, self.px) + alt_to_px(top, self.px)) / 2
            # label key, outermost layer at the top
            ly = 148 + (rows - 1 - i) * 22
            ax, ay = cx + r_mid * math.sin(0.75), cy - r_mid * math.cos(0.75)
            pygame.draw.line(s, LIGHT, (int(ax), int(ay)), (388, ly + 8))
            pygame.draw.rect(s, WHITE, (int(ax) - 1, int(ay) - 1, 3, 3))
            ui.text(s, name, (392, ly), WHITE, 14)
            ui.text(s, ("%d-%d km" % (lo, top)) if top < 10000 else "600+ km", (392, ly + 10), LIGHT, 14)
            lo = top
        kr = R + alt_to_px(100, self.px)
        pygame.draw.circle(s, YELLOW, (int(cx), int(cy)), int(kr), 1)
        kx, ky = cx - kr * math.sin(0.95), cy - kr * math.cos(0.95)
        ui.text(s, "KARMAN LINE 100 km", (int(kx) - 4, int(ky) - 18), YELLOW, 14, right=True)
        ui.text(s, "(edge of space)", (int(kx) - 4, int(ky) - 8), YELLOW, 14, right=True)

    def draw_other_body(self, s):
        """Ascent from the Moon, Mars or Bennu: no labelled Earth atmosphere."""
        s.fill(SPACE)
        for i in range(60):
            s.set_at(((i * 97) % W, (i * 53) % 150), (150, 150, 190))
        col = {"moon": (130, 130, 140), "mars": (170, 80, 50), "asteroid": (90, 80, 70)}.get(self.site, GREY)
        if self.site == "mars":
            pygame.draw.circle(s, (120, 80, 70), (self.cx, self.cy), self.R + 30)
            ui.text(s, "THIN CO2 ATMOSPHERE (1% of Earth's)", (130, 205), (230, 180, 160), 14)
        pygame.draw.circle(s, col, (self.cx, self.cy), self.R)
        name = {"moon": "THE MOON", "mars": "MARS", "asteroid": "BENNU"}.get(self.site, "")
        ui.text(s, "LAUNCH FROM %s" % name, (8, 8 if not self.mc.active else 70), YELLOW, 16)
        if self.site != "mars":
            ui.text(s, "No atmosphere: no Max-Q, no ascent heating!", (8, 24 if not self.mc.active else 86),
                    LIGHT, 14)

    def draw(self, s):
        if self.site != "earth":
            self.draw_other_body(s)
            self.draw_flight(s)
            return
        if self.bg is not None:
            self.draw_custom_bg(s)
            self.draw_flight(s)
            return
        s.fill(SPACE)
        for i in range(60):
            x, y = (i * 97) % W, (i * 53) % 150
            s.set_at((x, y), (150, 150, 190))
        cx, cy, R = self.cx, self.cy, self.R
        prev = 0
        for name, top, col in reversed(LAYERS):
            pygame.draw.circle(s, col, (cx, cy), int(R + alt_to_px(top)))
        # layer boundary lines + labels
        for name, top, col in LAYERS:
            r = R + alt_to_px(top)
            pygame.draw.circle(s, tuple(min(255, c + 40) for c in col), (cx, cy), int(r), 1)
        lo = 0
        for name, top, col in LAYERS:
            mid = R + (alt_to_px(lo) + min(alt_to_px(top), 165)) / 2
            x = 6
            ang = math.asin((x + 30 - cx) / mid)
            y = cy - mid * math.cos(ang)
            ui.text(s, name, (x, int(y) - 9), WHITE, 14)
            ui.text(s, ("%d-%d km" % (lo, top)) if top < 10000 else "600+ km", (x, int(y) + 1), LIGHT, 14)
            lo = top
        # Earth itself
        pygame.draw.circle(s, (30, 90, 40), (cx, cy), R)
        pygame.draw.circle(s, (40, 120, 200), (cx, cy), R, 6)
        pygame.draw.rect(s, (30, 90, 40), (0, 260, W, 10))
        # Karman line
        kr = R + alt_to_px(100)
        pygame.draw.circle(s, YELLOW, (cx, cy), int(kr), 1)
        ka = math.asin((170 - cx) / kr)
        ui.text(s, "KARMAN LINE 100 km (edge of space)", (130, int(cy - kr * math.cos(ka)) - 11), YELLOW, 14)
        self.draw_flight(s)

    def draw_flight(self, s):
        # trajectory
        if len(self.trail) > 1:
            pygame.draw.lines(s, (255, 120, 120), False, [(int(x), int(y)) for x, y in self.trail], 1)
        f = min(1.0, self.t / self.DURATION)
        x, y = self.pos(f)
        if self.boom_t is not None:
            art.explosion(s, x, y, min(1.0, self.boom_t / 1.5))
        else:
            pygame.draw.rect(s, RED, (int(x) - 2, int(y) - 2, 5, 5))
            pygame.draw.rect(s, WHITE, (int(x) - 1, int(y) - 1, 2, 2))
        # telemetry
        h = self.alt(f)
        ui.panel(s, (328, 4, 148, 80), fill=(10, 10, 30), border=CYAN)
        ui.text(s, "TELEMETRY", (334, 8), CYAN, 14)
        rows = [("ALTITUDE", "%.0f km" % h), ("VELOCITY", "%.2f km/s" % self.vel(f)),
                ("AIR TEMP", ("%.0f C" % air_temp(h)) if self.site == "earth" else
                 ("%.0f C" % (-60 - h * 0.5) if self.site == "mars" else "no air")),
                ("PRESSURE", "%.3f kPa" % ({"earth": 101.3, "mars": 0.6}.get(self.site, 0.0)
                                          * math.exp(-h / (8.5 if self.site == "earth" else 11.1)))),
                ("LAYER", layer_name(h) if self.site == "earth" else
                 ("THIN CO2 AIR" if self.site == "mars" and h < 60 else ("VACUUM" if self.site != "mars" else "SPACE")))]
        for i, (k, v) in enumerate(rows):
            ui.text(s, k, (334, 20 + i * 12), LIGHT, 14)
            ui.text(s, v, (472, 20 + i * 12), WHITE, 14, right=True)
        for i, (m, c) in enumerate(self.msgs):
            ui.text(s, m, (W - 6, 90 + i * 11), c, 14, right=True)
        self.mc.draw(s)
