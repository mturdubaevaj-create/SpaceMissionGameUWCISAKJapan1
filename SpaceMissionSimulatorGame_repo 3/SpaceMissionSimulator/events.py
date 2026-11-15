"""Random events. Each event is a Scene that ends by calling finish(result).

result = {"summary": str, "changes": {resource: delta}, "fail": reason|None,
          "encounter": 'pirate'|'astronaut'|None, "extra": callable(ms)|None}
To add an event: subclass EventScene and register it in EVENTS at the bottom.
"""
import math
import random

import pygame

import art
import ui
from scene import Scene, MissionControl
from settings import *

RES_NAMES = {"energy": "energy", "food": "food", "fuel": "fuel"}


class EventScene(Scene):
    music = "mission"
    title = "EVENT"

    def __init__(self, game, mscene):
        super().__init__(game)
        self.ms = game.mission
        self.mscene = mscene
        self.t = 0.0
        self.result = None
        self.mc = MissionControl(game, (4, 196, 472, 70))
        self.stars = art.Starfield(seed=21, decor=False)
        self.tutorial = bool(self.ms.level.get("tutorial"))

    def finish(self, result, sound=None):
        if self.result is not None:
            return
        self.result = result
        self.result_t = 0.0
        if sound:
            self.audio.play(sound)
        elif result.get("fail"):
            self.audio.play("fail")
        else:
            self.audio.play("success")

    def handle(self, e):
        if self.mc.handle(e):
            return True
        if self.result is not None:
            if self.result_t > 0.6 and ((e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or
                                        (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN))):
                self.mscene.on_event_done(self.result)
            return True
        if self.mc.active:
            return True
        return self.handle_event(e)

    def handle_event(self, e):
        return super().handle(e)

    def update(self, dt):
        self.mc.update(dt)
        if self.result is not None:
            self.result_t += dt
            return
        if self.mc.active:
            return
        self.t += dt
        self.update_event(dt)

    def update_event(self, dt):
        pass

    def draw_result(self, s):
        if self.result is None:
            return
        r = self.result
        bad = bool(r.get("fail"))
        ui.panel(s, (70, 70, 340, 110), fill=DARKRED if bad else (16, 50, 30), border=RED if bad else GREEN)
        ui.text(s, "MISSION FAILURE" if bad else "EVENT RESOLVED", (W // 2, 78), YELLOW, 20, center=True)
        ui.text_block(s, r.get("fail") or r.get("summary", ""), (82, 98, 316, 50), WHITE, 16)
        ch = r.get("changes") or {}
        parts = ["%s %+d" % (k.upper(), v) for k, v in ch.items() if v]
        if parts and not bad:
            ui.text(s, "  ".join(parts), (W // 2, 150), CYAN, 14, center=True)
        if self.result_t > 0.6:
            ui.text(s, "Click to continue", (W // 2, 165), LIGHT, 14, center=True)

    def header(self, s, txt, col=RED):
        ui.panel(s, (0, 0, W, 18), fill=(30, 10, 14), border=col)
        ui.text(s, txt, (W // 2, 3), YELLOW, 16, center=True)


def random_resource():
    return random.choice(["energy", "food", "fuel"])


# ------------------------------------------------------------------ asteroid field
class AsteroidEvent(EventScene):
    DURATION = 15.0

    def __init__(self, game, mscene):
        super().__init__(game, mscene)
        self.ship = pygame.transform.rotate(art.draw_ship(self.ms.design.c, flight=True), -90)
        self.y = 120.0
        self.rocks = []
        self.spawn = 0.0
        self.hits = 0
        self.inv = 0.0
        density = 1.0 + 0.4 * (self.ms.level["game"]["event_bias"].get("asteroid", 1.0) - 1.0)
        self.rate = 0.45 / density
        self.mc.tip("ev_asteroid", [
            "ASTEROID FIELD! Steer with the UP/DOWN arrow keys, W/S, or move the mouse.",
            "Each hit damages the hull. Survive for 15 seconds!",
        ], force=self.tutorial)

    def update_event(self, dt):
        keys = pygame.key.get_pressed()
        dy = 0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        if dy:
            self.y += dy * 130 * dt
        else:
            my = pygame.mouse.get_pos()[1]
            if pygame.mouse.get_focused():
                self.y += (my - self.y) * min(1.0, dt * 5)
        self.y = max(30, min(240, self.y))
        self.stars.update(dt, 160)
        self.spawn -= dt
        if self.spawn <= 0 and self.t < self.DURATION - 1.5:
            self.spawn = self.rate * random.uniform(0.6, 1.4)
            r = random.randint(4, 12)
            self.rocks.append([W + r, random.uniform(24, 250), random.uniform(90, 170) + self.t * 4, r,
                               random.uniform(0, 6)])
        self.inv = max(0.0, self.inv - dt)
        sw, sh = self.ship.get_size()
        sr = pygame.Rect(60 - sw // 2 + 6, int(self.y) - sh // 2 + 4, sw - 12, sh - 8)
        for rk in self.rocks:
            rk[0] -= rk[2] * dt
            rk[4] += dt * 2
            if self.inv <= 0 and sr.inflate(rk[3], rk[3]).collidepoint(rk[0], rk[1]):
                self.hits += 1
                self.inv = 1.0
                self.audio.play("hit")
                self.ms.apply({"integrity": -10})
                rk[0] = -100
                if self.ms.integrity <= 0:
                    self.finish({"fail": "Asteroid impacts destroyed the spacecraft."})
                    return
        self.rocks = [r for r in self.rocks if r[0] > -20]
        if self.t >= self.DURATION:
            if self.hits == 0:
                self.finish({"summary": "Perfect piloting! Not a scratch. You also scanned asteroid dust (+10 science).",
                             "changes": {"science": 10}})
            else:
                self.finish({"summary": "Made it through the asteroid field with %d hit%s." %
                                        (self.hits, "" if self.hits == 1 else "s")})

    def draw(self, s):
        self.stars.draw(s)
        for x, y, v, r, a in self.rocks:
            ast = art.planet("asteroid", r)
            ast = pygame.transform.rotate(ast, int(a * 30) // 90 * 90)
            s.blit(ast, (int(x) - ast.get_width() // 2, int(y) - ast.get_height() // 2))
        if self.inv <= 0 or int(self.t * 12) % 2 == 0:
            sw, sh = self.ship.get_size()
            s.blit(self.ship, (60 - sw // 2, int(self.y) - sh // 2))
            if int(self.t * 20) % 2:
                pygame.draw.rect(s, ORANGE, (60 - sw // 2 - 4, int(self.y) - 2, 6, 4))
        self.header(s, "ASTEROID FIELD - SURVIVE %ds   HITS: %d   HULL: %d%%" %
                    (max(0, self.DURATION - self.t) + 0.99, self.hits, self.ms.integrity))
        self.draw_result(s)
        self.mc.draw(s)


# ------------------------------------------------------------------ micrometeorite
class MicrometeoriteEvent(EventScene):
    GRACE = 8.0
    LIMIT = 22.0

    def __init__(self, game, mscene):
        super().__init__(game, mscene)
        n = 4 + (1 if not self.tutorial else 0) + int(self.ms.level["game"]["event_bias"].get("micrometeorite", 1) > 1)
        self.breaches = []
        for _ in range(n):
            self.breaches.append([random.randint(70, 410), random.randint(60, 170), 0])
        self.pressure = 100.0
        self.parts = []
        self.audio.play("hit")
        self.mc.tip("ev_micro", [
            "MICROMETEORITE STRIKE! Tiny space rocks punched holes in the hull and air is leaking!",
            "CLICK each hissing breach 3 times to weld it shut. If you're slow, hull integrity drops - and if the air runs out, it's over!",
        ], force=self.tutorial)

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.breaches:
                if b[2] < 3 and abs(e.pos[0] - b[0]) < 10 and abs(e.pos[1] - b[1]) < 10:
                    b[2] += 1
                    self.audio.play("repair" if b[2] == 3 else "click")
                    for _ in range(6):
                        self.parts.append([b[0], b[1], random.uniform(-40, 40), random.uniform(-40, 40), 0.3, YELLOW])
                    return True
        return False

    def update_event(self, dt):
        open_ = [b for b in self.breaches if b[2] < 3]
        self.pressure -= len(open_) * 0.9 * dt
        if self.t > self.GRACE:
            for _ in open_:
                self.ms.integrity = max(0.0, self.ms.integrity - 1.5 * dt)
        for b in open_:
            if random.random() < 0.5:
                self.parts.append([b[0], b[1], random.uniform(-15, 15), random.uniform(-30, -5), 0.6, LIGHT])
        for p in self.parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0]
        if not open_:
            fast = self.t <= self.GRACE
            self.finish({"summary": "All breaches sealed in %.1f s! %s" %
                                    (self.t, "Lightning fast - no extra damage." if fast else
                                     "The slow repair cost some hull integrity.")})
        elif self.pressure <= 0 or self.t > self.LIMIT or self.ms.integrity <= 0:
            self.finish({"fail": "Cabin depressurised! The hull breaches were not sealed in time."})

    def draw(self, s):
        s.fill((20, 20, 30))
        # ship interior cross-section
        ui.panel(s, (40, 30, 400, 160), fill=(70, 74, 90), border=LIGHT)
        for x in range(50, 430, 30):
            pygame.draw.line(s, (60, 62, 78), (x, 34), (x, 186))
        for y in range(40, 186, 24):
            pygame.draw.line(s, (60, 62, 78), (44, y), (436, y))
        pygame.draw.rect(s, (40, 40, 56), (200, 150, 80, 36))  # console
        s.blit(art.character("player", 2), (220, 118))
        for b in self.breaches:
            if b[2] < 3:
                pulse = int(self.t * 8) % 2
                pygame.draw.circle(s, BLACK, (b[0], b[1]), 5 + pulse)
                pygame.draw.circle(s, RED, (b[0], b[1]), 7 + pulse, 1)
                for i in range(b[2]):
                    pygame.draw.rect(s, YELLOW, (b[0] - 6 + i * 5, b[1] + 10, 3, 3))
            else:
                pygame.draw.rect(s, (150, 150, 160), (b[0] - 5, b[1] - 5, 10, 10))
                pygame.draw.rect(s, GREY, (b[0] - 5, b[1] - 5, 10, 10), 1)
        for p in self.parts:
            pygame.draw.rect(s, p[5], (int(p[0]), int(p[1]), 2, 2))
        open_ = sum(1 for b in self.breaches if b[2] < 3)
        self.header(s, "HULL BREACH!  OPEN: %d   AIR: %d%%   HULL: %d%%   %s" % (
            open_, max(0, self.pressure), self.ms.integrity,
            ("GRACE %.0fs" % (self.GRACE - self.t)) if self.t < self.GRACE else "HULL DAMAGE!"))
        self.draw_result(s)
        self.mc.draw(s)


# ------------------------------------------------------------------ malfunction
SYSTEMS = {
    "generator": dict(name="POWER GENERATOR", symptom="Lights are flickering and the batteries aren't charging.",
                      bad=["OUTPUT: 12% UNSTABLE", "VOLTAGE: 3.1V (LOW)"], ok=["OUTPUT: 98%", "VOLTAGE: 28V"]),
    "fuel": dict(name="FUEL SYSTEM", symptom="A strange smell, and tank pressure keeps dropping.",
                 bad=["TANK P: 41% FALLING", "VALVE 3: STUCK"], ok=["TANK P: 100%", "VALVES: SEALED"]),
    "nav": dict(name="NAVIGATION", symptom="The star tracker shows the stars drifting the wrong way.",
                bad=["HEADING ERR: 14 DEG", "GYRO: DRIFT"], ok=["HEADING ERR: 0.1", "GYRO: LOCKED"]),
    "life": dict(name="LIFE SUPPORT", symptom="CO2 alarm! The air scrubbers have gone quiet.",
                 bad=["CO2: 2.1% RISING", "FAN: 0 RPM"], ok=["CO2: 0.04%", "FAN: 3200 RPM"]),
}
ARROWS = {pygame.K_UP: "UP", pygame.K_DOWN: "DOWN", pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT"}


class MalfunctionEvent(EventScene):
    def __init__(self, game, mscene):
        super().__init__(game, mscene)
        ms = self.ms
        w = {"generator": 1.2 - ms.en["reliability"], "fuel": 1.2 - ms.eng["reliability"], "nav": 0.15,
             "life": 0.1}
        self.fault = random.choices(list(w), weights=list(w.values()))[0]
        self.stage = "diagnose"
        self.wrong = 0
        self.tries = 0
        self.order = list(SYSTEMS)
        self.sys_buttons = []
        for i, k in enumerate(self.order):
            x = 20 + (i % 2) * 224
            y = 70 + (i // 2) * 58
            self.sys_buttons.append((pygame.Rect(x, y, 216, 52), k))
        self.arrow_buttons = []
        for i, (key, name) in enumerate(ARROWS.items()):
            self.arrow_buttons.append(ui.Button((120 + i * 62, 160, 56, 22), name,
                                                lambda k=key: self.input_arrow(k), color=BLUE, size=16))
        self.mc.tip("ev_malfunction", [
            "EQUIPMENT FAILURE! First DIAGNOSE: read the symptom and the readouts, then click the broken system.",
            "Then REPAIR it: memorise the arrow sequence and type it back with the arrow keys.",
        ], force=self.tutorial)

    # ---------------------------------------------------------- repair mini-games
    # Power / life support -> WIRING, navigation -> STAR TRACKER ALIGNMENT,
    # fuel system -> valve memory sequence (the original repair).
    WIRES = [("28V POWER BUS", RED), ("O2 SENSOR", CYAN), ("CABIN HEATER", ORANGE), ("COMMS ARRAY", GREEN),
             ("SCRUBBER FAN", YELLOW)]

    def start_repair(self):
        self.flash = None
        if self.fault in ("generator", "life"):
            n = 3 if self.tutorial else 4
            wires = random.sample(self.WIRES, n)
            left = list(range(n))
            right = list(range(n))
            random.shuffle(left)
            random.shuffle(right)
            self.wires = wires
            self.wire_left = {i: pygame.Rect(70, 66 + row * 30, 16, 12) for row, i in enumerate(left)}
            self.wire_right = {i: pygame.Rect(300, 66 + row * 30, 16, 12) for row, i in enumerate(right)}
            self.wire_done = set()
            self.dragging = None
            self.wire_errors = 0
            self.repair_t = 0.0
            self.repair_limit = 30.0 if self.tutorial else 22.0
            self.stage = "wires"
            self.mc.tip("ev_wires", "WIRING REPAIR! Drag each loose wire on the left to the socket with the "
                                    "same colour on the right. Wrong connections spark and waste power!",
                        force=self.tutorial)
        elif self.fault == "nav":
            self.star = [240.0, 120.0]
            self.drift = [random.choice([-1, 1]) * random.uniform(14, 20),
                          random.choice([-1, 1]) * random.uniform(8, 14)]
            self.cross = [240.0 + random.choice([-90, 90]), 120.0 + random.choice([-45, 45])]
            self.lock = 0.0
            self.repair_t = 0.0
            self.repair_limit = 28.0 if self.tutorial else 20.0
            self.stage = "align"
            self.mc.tip("ev_align", "COURSE CORRECTION! The star tracker lost its guide star. Steer the crosshair "
                                    "onto the yellow star with the ARROW KEYS / WASD and hold it there until it locks.",
                        force=self.tutorial)
        else:
            self.new_sequence()

    def repair_done(self):
        self.audio.play("repair")
        self.finish({"summary": "%s repaired! Engineering data logged (+8 science)." % SYSTEMS[self.fault]["name"],
                     "changes": {"science": 8}})

    def handle_repair(self, e):
        if self.stage != "wires":
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in self.wire_left.items():
                if i not in self.wire_done and r.inflate(10, 10).collidepoint(e.pos):
                    self.dragging = i
                    self.audio.play("click")
                    return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.dragging is not None:
            i = self.dragging
            self.dragging = None
            for j, r in self.wire_right.items():
                if r.inflate(14, 14).collidepoint(e.pos) and j not in self.wire_done:
                    if i == j:
                        self.wire_done.add(i)
                        self.audio.play("coin")
                        if len(self.wire_done) == len(self.wires):
                            self.repair_done()
                    else:
                        self.wire_errors += 1
                        self.audio.play("deny")
                        self.ms.apply({"energy": -4})
                        self.flash = "ZAP! Wrong socket (-4%% energy). Mistakes: %d/3" % self.wire_errors
                        if self.wire_errors >= 3:
                            self.consequence("Too many wrong connections shorted the circuit.")
                    return True
            return True
        return False

    def update_repair(self, dt):
        if self.stage not in ("wires", "align"):
            return
        self.repair_t += dt
        if self.stage == "align":
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
            self.cross[0] = max(40, min(440, self.cross[0] + dx * 70 * dt))
            self.cross[1] = max(40, min(190, self.cross[1] + dy * 70 * dt))
            # the ship slowly rotates, so the star drifts across the view (bouncing at the edges)
            for k, (lo, hi) in enumerate(((60, 420), (50, 180))):
                self.star[k] += self.drift[k] * dt
                if not lo <= self.star[k] <= hi:
                    self.drift[k] *= -1
                    self.star[k] = max(lo, min(hi, self.star[k]))
            if math.hypot(self.cross[0] - self.star[0], self.cross[1] - self.star[1]) < 10:
                self.lock += dt
                if int(self.lock * 6) != int((self.lock - dt) * 6):
                    self.audio.play("click")
            else:
                self.lock = max(0.0, self.lock - dt * 0.5)
            if self.lock >= 3.0:
                self.repair_done()
                return
        if self.repair_t > self.repair_limit and self.result is None:
            self.consequence("Ran out of time before the repair was finished.")

    def draw_repair(self, s):
        left = max(0.0, self.repair_limit - self.repair_t)
        if self.stage == "wires":
            ui.panel(s, (50, 40, 380, 26 + 30 * len(self.wires)), fill=(70, 72, 84), border=LIGHT)
            for x, y in ((56, 46), (420, 46), (56, 36 + 30 * len(self.wires)), (420, 36 + 30 * len(self.wires))):
                pygame.draw.circle(s, (40, 40, 50), (x, y + 14), 3)
            ui.text(s, "JUNCTION BOX - %s" % SYSTEMS[self.fault]["name"], (66, 44), YELLOW, 14)
            for i, r in self.wire_left.items():
                name, col = self.wires[i]
                pygame.draw.rect(s, col, r)
                pygame.draw.line(s, col, (50, r.centery), (r.x, r.centery), 3)
            for j, r in self.wire_right.items():
                name, col = self.wires[j]
                pygame.draw.rect(s, (30, 30, 36), r)
                pygame.draw.rect(s, col, r, 2)
                ui.text(s, name, (r.right + 6, r.y), WHITE, 14)
            for i in self.wire_done:
                a, b = self.wire_left[i], self.wire_right[i]
                pygame.draw.line(s, self.wires[i][1], a.midright, b.midleft, 3)
            if self.dragging is not None:
                a = self.wire_left[self.dragging]
                pygame.draw.line(s, self.wires[self.dragging][1], a.midright, pygame.mouse.get_pos(), 3)
            ui.text(s, "Drag each wire to the matching socket   TIME %.0f s" % left,
                    (W // 2, 74 + 30 * len(self.wires)), LIGHT, 14, center=True)
        else:
            ui.panel(s, (30, 30, 420, 168), fill=(6, 8, 20), border=CYAN)
            for i in range(40):
                x = 36 + (i * 137) % 408
                y = 36 + (i * 71) % 156
                s.set_at((x, y), (120, 120, 160))
            sx, sy = int(self.star[0]), int(self.star[1])
            pygame.draw.circle(s, YELLOW, (sx, sy), 3)
            pygame.draw.circle(s, (120, 100, 30), (sx, sy), 10, 1)
            cx, cy = int(self.cross[0]), int(self.cross[1])
            col = GREEN if math.hypot(cx - sx, cy - sy) < 10 else WHITE
            pygame.draw.line(s, col, (cx - 9, cy), (cx - 3, cy))
            pygame.draw.line(s, col, (cx + 3, cy), (cx + 9, cy))
            pygame.draw.line(s, col, (cx, cy - 9), (cx, cy - 3))
            pygame.draw.line(s, col, (cx, cy + 3), (cx, cy + 9))
            ui.text(s, "STAR TRACKER", (38, 34), CYAN, 14)
            pygame.draw.rect(s, DARK, (140, 184, 200, 8))
            pygame.draw.rect(s, GREEN, (140, 184, int(200 * min(1.0, self.lock / 3.0)), 8))
            ui.text(s, "LOCK", (134, 182), GREEN, 14, right=True)
            ui.text(s, "%.0f s" % left, (346, 182), LIGHT, 14)

    def new_sequence(self):
        n = 4 if self.tutorial else 5
        self.seq = [random.choice(list(ARROWS)) for _ in range(n)]
        self.entered = []
        self.show_t = 0.0
        self.stage = "show"

    def handle_event(self, e):
        if self.handle_repair(e):
            return True
        if self.stage == "diagnose" and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, k in self.sys_buttons:
                if r.collidepoint(e.pos):
                    if k == self.fault:
                        self.audio.play("select")
                        self.start_repair()
                    else:
                        self.wrong += 1
                        self.audio.play("deny")
                        self.ms.apply({"energy": -6})
                        self.flash = "%s checks out fine. (-6%% energy)" % SYSTEMS[k]["name"]
                        if self.wrong >= 2:
                            self.consequence("Couldn't find the fault in time.")
                    return True
        if self.stage == "input":
            if e.type == pygame.KEYDOWN and e.key in ARROWS:
                self.input_arrow(e.key)
                return True
            for b in self.arrow_buttons:
                if b.handle(e, None):
                    return True
        return False

    def input_arrow(self, key):
        if self.stage != "input":
            return
        self.entered.append(key)
        i = len(self.entered) - 1
        if self.entered[i] != self.seq[i]:
            self.audio.play("deny")
            self.tries += 1
            if self.tries >= 2:
                self.consequence("The repair sequence failed twice.")
            else:
                self.flash = "Wrong sequence! Sparks fly... try again (-5% energy)"
                self.ms.apply({"energy": -5})
                self.new_sequence()
            return
        self.audio.play("click")
        if len(self.entered) == len(self.seq):
            self.audio.play("repair")
            self.finish({"summary": "%s repaired! Engineering data logged (+8 science)." % SYSTEMS[self.fault]["name"],
                         "changes": {"science": 8}})

    def consequence(self, why):
        f = self.fault
        if f == "generator":
            def ex(ms):
                ms.gen_offline = 2
            self.finish({"summary": why + " The generator is offline for 2 turns! Use ECO mode.",
                         "changes": {"energy": -20}, "extra": ex}, "fail")
        elif f == "fuel":
            if self.ms.design["engine"] == "nuclear":
                self.finish({"fail": why + " The nuclear engine overheated and EXPLODED."})
            else:
                self.finish({"summary": why + " A fuel leak drained a quarter of your propellant!",
                             "changes": {"fuel": -25}}, "fail")
        elif f == "nav":
            def ex(ms):
                ms.turns_total += 1
                ms.burn_plan.insert(len(ms.burn_plan) - 1, 0.0)
            self.finish({"summary": why + " Navigation drift: the trip takes one extra turn (more food used).",
                         "extra": ex}, "fail")
        else:
            self.finish({"fail": why + " Life support failed - the crew could not breathe."})

    def update_event(self, dt):
        self.stars.update(dt, 20)
        self.update_repair(dt)
        if self.stage == "show":
            self.show_t += dt
            if self.show_t > 0.7 * len(self.seq) + 0.6:
                self.stage = "input"

    def draw(self, s):
        self.stars.draw(s, 0.5)
        self.header(s, "EQUIPMENT MALFUNCTION - %s" % ("DIAGNOSE THE FAULT" if self.stage == "diagnose" else "REPAIR"))
        sysd = SYSTEMS[self.fault]
        if self.stage in ("wires", "align"):
            self.draw_repair(s)
        elif self.stage == "diagnose":
            ui.panel(s, (20, 24, 440, 40), fill=(40, 20, 20), border=ORANGE)
            ui.text(s, "SYMPTOM:", (28, 28), ORANGE, 14)
            ui.text_block(s, sysd["symptom"], (28, 40, 424, 22), WHITE, 16)
            mp = pygame.mouse.get_pos()
            for r, k in self.sys_buttons:
                ui.panel(s, r, fill=(30, 30, 60) if r.collidepoint(mp) else NAVY, border=CYAN)
                ui.text(s, SYSTEMS[k]["name"], (r.x + 6, r.y + 4), CYAN, 16)
                lines = SYSTEMS[k]["bad"] if k == self.fault else SYSTEMS[k]["ok"]
                for i, l in enumerate(lines):
                    ui.text(s, l, (r.x + 6, r.y + 20 + i * 12), WHITE, 14)
            ui.text(s, "Wrong guesses: %d/2" % self.wrong, (W // 2, 190), LIGHT, 14, center=True)
        else:
            ui.panel(s, (60, 40, 360, 150), fill=NAVY, border=CYAN)
            ui.text(s, "REPAIRING: " + sysd["name"], (W // 2, 46), CYAN, 16, center=True)
            if self.stage == "show":
                ui.text(s, "MEMORISE THE SEQUENCE!", (W // 2, 64), YELLOW, 16, center=True)
                i = int(self.show_t / 0.7)
                if i < len(self.seq) and (self.show_t % 0.7) < 0.55:
                    ui.text(s, ARROWS[self.seq[i]], (W // 2, 100), WHITE, 24, center=True, scale=2)
                    ui.text(s, "%d / %d" % (i + 1, len(self.seq)), (W // 2, 140), LIGHT, 14, center=True)
            else:
                ui.text(s, "TYPE IT BACK WITH THE ARROW KEYS", (W // 2, 64), YELLOW, 16, center=True)
                for i in range(len(self.seq)):
                    x = W // 2 - len(self.seq) * 22 + i * 44 + 22
                    done = i < len(self.entered)
                    ui.panel(s, (x - 20, 90, 40, 30), fill=DARKGREEN if done else DARK, border=GREY)
                    if done:
                        ui.text(s, ARROWS[self.entered[i]][:1], (x, 98), WHITE, 20, center=True)
                for b in self.arrow_buttons:
                    b.draw(s)
        if getattr(self, "flash", None) and self.result is None:
            ui.text(s, self.flash, (W // 2, 178 if self.stage == "diagnose" else 186), RED, 14, center=True)
        self.draw_result(s)
        self.mc.draw(s)


# ------------------------------------------------------------------ solar flare
# Walk the astronaut through the ship to the best shelter before the flare hits.
# Rooms: (id, label, crew damage, hint). Damage is reduced a little by a strong heat shield.
FLARE_ROOMS = {
    "pantry": ("PANTRY / WATER", 8, "Food and water tanks absorb radiation"),
    "shelter": ("STORM SHELTER", 3, "Purpose-built radiation shelter"),
    "engine": ("ENGINE BAY", 22, "Engines and fuel tanks block some of it"),
    "quarters": ("CREW QUARTERS", 32, "Thin walls - little protection"),
    "cockpit": ("COCKPIT", 48, "Big windows facing the Sun!"),
}


class FlareEvent(EventScene):
    LIMIT = 12.0
    SPEED = 85.0

    def __init__(self, game, mscene):
        super().__init__(game, mscene)
        if self.tutorial:
            self.LIMIT = 16.0
        # layout: engine bay at the back (left), cockpit at the nose (right),
        # two side rooms off the corridor; pantry/quarters swap places each time.
        top, bottom = random.sample(["pantry", "quarters"], 2)
        self.rooms = [
            (pygame.Rect(44, 64, 92, 132), "engine"),
            (pygame.Rect(206, 30, 112, 82), top),
            (pygame.Rect(206, 152, 112, 72), bottom),
            (pygame.Rect(384, 74, 64, 112), "cockpit"),
        ]
        if self.ms.ship["storm_shelter"]:
            self.rooms.append((pygame.Rect(150, 30, 46, 82), "shelter"))
        self.corridor = pygame.Rect(136, 112, 248, 40)
        doors = [pygame.Rect(130, 116, 12, 32), pygame.Rect(240, 100, 40, 20), pygame.Rect(240, 140, 40, 20),
                 pygame.Rect(378, 116, 12, 32)]
        if self.ms.ship["storm_shelter"]:
            doors.append(pygame.Rect(160, 100, 26, 20))
        self.walkable = [r for r, k in self.rooms] + [self.corridor] + doors
        self.px, self.py = 170.0, 132.0
        import nasa_data
        self.real_flare, self.flare_mult = nasa_data.random_flare()
        self.audio.play("alarm")
        self.mc.tip("ev_flare", [
            "SOLAR FLARE! A blast of radiation from the Sun is on its way. Get the astronaut to shelter!",
            "Move with the ARROW KEYS or WASD. When the timer hits zero, the room you are in decides how much "
            "CREW HEALTH you lose.",
            "Dense stuff like water and food absorbs radiation best. Stay out of the corridor - it has no shielding!",
        ], force=self.tutorial)

    def room_at(self, x, y):
        for r, k in self.rooms:
            if r.inflate(-6, -6).collidepoint(x, y):
                return k
        return None

    def can_stand(self, x, y):
        return any(r.inflate(-6, -6).collidepoint(x, y) for r in self.walkable)

    def update_event(self, dt):
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if dx or dy:
            n = math.hypot(dx, dy)
            nx = self.px + dx / n * self.SPEED * dt
            ny = self.py + dy / n * self.SPEED * dt
            if self.can_stand(nx, self.py):
                self.px = nx
            if self.can_stand(self.px, ny):
                self.py = ny
        if self.t >= self.LIMIT:
            self.resolve()

    def resolve(self):
        ms = self.ms
        room = self.room_at(self.px, self.py)

        def panels(m):
            if m.en["solar"]:
                m.solar_degrade *= 0.85

        note = " Solar panels lost 15% output." if ms.en["solar"] else ""
        if room is None:
            self.finish({"fail": "Caught in the corridor when the flare hit - no shielding at all. "
                                 "The crew received a lethal dose of radiation."})
            return
        name, dmg, hint = FLARE_ROOMS[room]
        dmg = round(dmg * self.flare_mult * (1 - 0.3 * ms.pct("shield") / 100))
        changes = {"crew": -dmg}
        good = room in ("pantry", "shelter")
        if good:
            changes["science"] = 12
        msg = "Real %s flare! Sheltered in the %s: %s. Crew health -%d." % (
            self.real_flare["cls"], name.lower(), hint.lower(), dmg)
        if good:
            msg += " Flare data recorded (+12 science)."
        self.finish({"summary": msg + note, "changes": changes, "extra": panels}, None if good else "fail")

    def draw(self, s):
        t = self.t
        s.fill((14, 12, 26))
        sun = art.planet("sun", 26)
        s.blit(sun, (W - 56, -26))
        if t > self.LIMIT - 3 and int(t * 8) % 2 == 0:
            glow = pygame.Surface((W, H), pygame.SRCALPHA)
            glow.fill((255, 140, 40, 40))
            s.blit(glow, (0, 0))
        # hull outline
        pygame.draw.rect(s, (60, 62, 80), (36, 24, 420, 206), border_radius=18)
        pygame.draw.rect(s, (110, 112, 130), (36, 24, 420, 206), 2, border_radius=18)
        pygame.draw.rect(s, (52, 54, 70), self.corridor)
        for r in self.walkable[len(self.rooms) + 1:]:
            pygame.draw.rect(s, (52, 54, 70), r)
        here = self.room_at(self.px, self.py)
        colors = {"pantry": (60, 90, 70), "shelter": (50, 80, 110), "engine": (90, 70, 50),
                  "quarters": (70, 60, 90), "cockpit": (60, 70, 100)}
        for r, k in self.rooms:
            pygame.draw.rect(s, colors[k], r)
            pygame.draw.rect(s, YELLOW if k == here else (140, 140, 160), r, 1)
            name = FLARE_ROOMS[k][0]
            ui.text(s, name, (r.centerx, r.y + 3), WHITE, 12 if r.w < 70 else 14, center=True)
            self.draw_props(s, r, k)
        ui.text(s, "CORRIDOR", (self.corridor.centerx, self.corridor.y + 2), GREY, 12, center=True)
        # astronaut
        spr = art.character("player", 1)
        s.blit(spr, (int(self.px) - spr.get_width() // 2, int(self.py) - spr.get_height() // 2))
        left = max(0.0, self.LIMIT - t)
        where = FLARE_ROOMS[here][0] if here else "CORRIDOR - NO SHIELDING!"
        self.header(s, "SOLAR FLARE HITS IN %.1f s   |   YOU ARE IN: %s" % (left, where),
                    RED if here is None else ORANGE)
        f = self.real_flare
        ui.text(s, "Based on a REAL %s-class solar flare, %s (active region %s) - NASA DONKI" % (
            f["cls"], f["date"], f["region"]), (W // 2, 234), YELLOW, 14, center=True)
        ui.text(s, "Arrows / WASD to move", (W // 2, 248), LIGHT, 14, center=True)
        self.draw_result(s)
        self.mc.draw(s)

    def draw_props(self, s, r, k):
        if k == "pantry":
            for i in range(6):
                pygame.draw.rect(s, (150, 104, 64), (r.x + 8 + (i % 3) * 14, r.bottom - 26 + (i // 3) * 10, 10, 8))
            pygame.draw.rect(s, (70, 130, 200), (r.right - 26, r.bottom - 34, 16, 26))
        elif k == "shelter":
            pygame.draw.rect(s, (90, 130, 170), (r.x + 6, r.bottom - 22, r.w - 12, 14), 1)
        elif k == "engine":
            for i in range(2):
                pygame.draw.circle(s, (130, 130, 140), (r.centerx, r.y + 44 + i * 40), 12, 2)
        elif k == "quarters":
            for i in range(2):
                pygame.draw.rect(s, (180, 180, 200), (r.x + 8, r.y + 22 + i * 22, 30, 10))
        elif k == "cockpit":
            pygame.draw.rect(s, CYAN, (r.right - 10, r.y + 20, 6, r.h - 40))
            pygame.draw.rect(s, (40, 40, 56), (r.x + 8, r.centery - 8, 20, 16))


# ------------------------------------------------------------------ dialogue events
class PirateEvent(EventScene):
    def __init__(self, game, mscene):
        super().__init__(game, mscene)
        self.qs = game.facts.quiz(3)
        self.variant = art.pick_variant("pirate")   # sometimes the new pirate look
        self.i = 0
        self.correct = 0
        self.feedback = None
        self.fb_t = 0.0
        self.make_buttons()
        self.mc.tip("ev_pirate", [
            "An ALIEN PIRATE! He loves space trivia. Answer his questions using facts Zorp taught you.",
            "3 right: a reward. Fewer right: he steals supplies. 0 right... he takes the whole ship!",
        ], force=self.tutorial)

    def make_buttons(self):
        self.buttons = []
        if self.i >= len(self.qs):
            return
        q = self.qs[self.i]
        for j, opt in enumerate(q["options"]):
            self.buttons.append(ui.Button((120 + (j % 2) * 122, 150 + (j // 2) * 22, 118, 18), opt[:22],
                                          lambda j=j: self.answer(j), color=PURPLE, size=14, tooltip=opt))

    def answer(self, j):
        if self.feedback:
            return
        q = self.qs[self.i]
        right = j == q["answer"]
        if right:
            self.correct += 1
            self.audio.play("coin")
            self.feedback = ("CORRECT! Arr, ye know yer space...", GREEN)
        else:
            self.audio.play("deny")
            self.feedback = ("WRONG! The answer was: " + q["options"][q["answer"]], RED)
        self.fb_t = 0.0

    def update_event(self, dt):
        if self.feedback:
            self.fb_t += dt
            if self.fb_t > 2.2:
                self.feedback = None
                self.i += 1
                self.make_buttons()
                if self.i >= len(self.qs):
                    self.resolve()

    def resolve(self):
        c = self.correct
        n = len(self.qs)
        if c == n:
            r = random_resource()
            self.finish({"summary": "All %d correct! The pirate is impressed and gives you supplies (+30%% %s)." % (n, r),
                         "changes": {r: 30}, "encounter": "pirate"}, "coin")
        elif c == n - 1:
            r = random_resource()
            self.finish({"summary": "%d/%d correct. The pirate steals a little %s (-12%%)." % (c, n, r),
                         "changes": {r: -12}, "encounter": "pirate"}, "fail")
        elif c >= 1:
            r1, r2 = random.sample(["energy", "food", "fuel"], 2)
            self.finish({"summary": "Only %d/%d correct! The pirate raids your %s and %s (-25%% each)." % (c, n, r1, r2),
                         "changes": {r1: -25, r2: -25}, "encounter": "pirate"}, "fail")
        else:
            self.finish({"fail": "0/%d correct... The alien pirate seized your spacecraft!" % n})

    def draw(self, s):
        self.stars.draw(s)
        self.header(s, "ALIEN PIRATE ENCOUNTER", PURPLE)
        bob = int(math.sin(self.t * 3) * 2)
        spr = art.character("pirate", 4, 0, self.variant)
        s.blit(spr, (24, 94 - spr.get_height() + bob))
        s.blit(art.character("player", 4), (W - 24 - 64, 30))
        ui.text(s, "CAPTAIN ZYXTAR", (56, 96), PINK, 14, center=True)
        ui.text(s, self.game.save.data["player_name"], (W - 56, 96), CYAN, 14, center=True)
        ui.panel(s, (100, 26, 280, 118), fill=(30, 14, 40), border=PURPLE)
        if self.i < len(self.qs):
            q = self.qs[self.i]
            ui.text(s, "QUESTION %d OF %d   (correct: %d)" % (self.i + 1, len(self.qs), self.correct), (108, 30), YELLOW, 14)
            ui.text_block(s, '"Arrr! Answer me this, earthling: ' + q["q"] + '"', (108, 44, 264, 60), WHITE, 16)
            if self.feedback:
                ui.text_block(s, self.feedback[0], (108, 106, 264, 30), self.feedback[1], 14)
            else:
                for b in self.buttons:
                    b.draw(s)
        self.draw_result(s)
        self.mc.draw(s)


NAMES = ["Cmdr. Rivera", "Dr. Okafor", "Lt. Tanaka", "Major Petrova", "Cmdr. Haddad", "Dr. Lindqvist"]


class AstronautEvent(EventScene):
    def __init__(self, game, mscene):
        super().__init__(game, mscene)
        self.fact, self.statement, self.truth = game.facts.statement()
        self.name = random.choice(NAMES)
        self.variant = art.pick_variant("pirate")
        self.stranded_variant = art.pick_variant("stranded")   # sometimes the new astronaut look
        self.revealed = False
        self.buttons = [
            ui.Button((40, 176, 190, 20), "TRUE - RESCUE THEM", lambda: self.decide(True), color=DARKGREEN, size=14),
            ui.Button((250, 176, 190, 20), "FALSE - IMPOSTOR!", lambda: self.decide(False), color=DARKRED, size=14),
        ]
        self.mc.tip("ev_astronaut", [
            "A stranded astronaut... or an alien in disguise? Aliens can't help getting NASA facts wrong!",
            "If the fact is TRUE, it's a real astronaut - rescue them. If it's FALSE, it's an impostor - leave them!",
        ], force=self.tutorial)

    def decide(self, rescue):
        if self.result is not None:
            return
        self.buttons = []
        truth = self.truth
        correct_text = " (Fact: %s)" % self.fact["true_s"]
        if truth and rescue:
            r = random_resource()
            self.finish({"summary": "%s is a real astronaut and thanks you with supplies (+25%% %s)!%s" %
                                    (self.name, r, correct_text), "changes": {r: 25}, "encounter": "astronaut"}, "coin")
        elif truth and not rescue:
            r = random_resource()
            self.finish({"summary": "That fact was TRUE - you abandoned a real astronaut! Mission Control fines you "
                                    "(-15%% %s).%s" % (r, correct_text), "changes": {r: -15}, "encounter": "astronaut"},
                        "fail")
        elif not truth and not rescue:
            self.revealed = True
            self.finish({"summary": "Correct! The fact was FALSE. The 'astronaut' peels off its mask - an alien! "
                                    "You escape safely.%s" % correct_text, "encounter": "astronaut"}, "success")
        else:
            self.revealed = True
            self.finish({"fail": "You rescued an IMPOSTOR! The alien threw off its disguise and hijacked your "
                                 "spacecraft. The fact was false.%s" % correct_text})

    def draw(self, s):
        self.stars.draw(s)
        self.header(s, "DISTRESS SIGNAL - STRANDED ASTRONAUT?", CYAN)
        bob = int(math.sin(self.t * 1.5) * 3)
        if self.revealed:
            spr = art.character("pirate", 4, 0, self.variant)
        else:
            spr = art.character("stranded", 4, 0, self.stranded_variant)
        s.blit(spr, (24, 98 - spr.get_height() + bob))
        s.blit(art.character("player", 4), (W - 24 - 64, 34))
        ui.text(s, "???" if self.revealed else self.name, (56, 100), CYAN, 14, center=True)
        ui.text(s, self.game.save.data["player_name"], (W - 56, 100), CYAN, 14, center=True)
        ui.panel(s, (100, 26, 280, 140), fill=(14, 30, 44), border=CYAN)
        ui.text_block(s, '"Help! I\'m %s, my ship broke down. I\'m a REAL astronaut - here\'s a NASA fact to '
                         'prove it:"' % self.name, (108, 32, 264, 44), LIGHT, 14)
        ui.text_block(s, '"' + self.statement + '"', (108, 80, 264, 60), YELLOW, 16)
        ui.text(s, "Is the fact TRUE or FALSE?", (W // 2, 148), WHITE, 14, center=True)
        for b in self.buttons:
            b.draw(s)
        self.draw_result(s)
        self.mc.draw(s)


# ------------------------------------------------------------------ docking
class DockingEvent(EventScene):
    """A space station is nearby: dock for supplies (optional). Gentle drift physics.
    Speeds are shown in m/s (1 px/s = 0.03 m/s); limits for a GOOD dock are like real ones, scaled."""
    ACC = 20.0          # px/s^2 per thruster
    ROT = 30.0          # deg/s^2
    PORT = (420, 135)   # docking port position
    LIMIT = 60.0
    GOOD = dict(speed=0.4, offset=4, angle=5)
    OK = dict(speed=0.8, offset=9, angle=12)

    def __init__(self, game, mscene):
        super().__init__(game, mscene)
        self.stage = "offer"
        img = pygame.transform.rotate(art.draw_ship(self.ms.design.c, flight=True), -90)
        self.ship = pygame.transform.smoothscale(img, (int(img.get_width() * 0.6), int(img.get_height() * 0.6)))
        self.buttons = [
            ui.Button((120, 200, 110, 22), "REQUEST DOCKING", self.begin, color=DARKGREEN, size=14, sound="select"),
            ui.Button((250, 200, 110, 22), "FLY PAST", self.decline, color=DARK, size=14, sound="back"),
        ]
        self.mc.tip("ev_dock_offer", "A space station is nearby! Docking could refill fuel, energy and food - "
                                     "but a bad docking damages the ship, and crashing ends the mission.",
                    force=self.tutorial)

    def decline(self):
        self.buttons = []
        self.finish({"summary": "You flew past the station. No supplies, no risk."}, "select")

    def begin(self):
        self.buttons = []
        self.stage = "fly"
        self.t = 0.0
        self.x, self.y = 90.0, self.PORT[1] + random.choice([-1, 1]) * random.uniform(25, 45)
        self.vx, self.vy = 8.0, 0.0
        self.ang = random.choice([-1, 1]) * random.uniform(8, 16)
        self.vang = 0.0
        self.mc.tip("ev_dock", [
            "DOCKING! Like a real spacecraft, you keep drifting until you fire thrusters the other way.",
            "LEFT/RIGHT (A/D): slow down / speed up.  UP/DOWN (W/S): move up/down.  Q/E: rotate.  X: abort.",
            "Touch the docking port SLOWLY (under 0.4 m/s), CENTRED and STRAIGHT. All three green = perfect dock!",
        ], force=True)

    def speed(self):
        return self.vx * 0.03

    def offset(self):
        return abs(self.y - self.PORT[1])

    def handle_event(self, e):
        if self.stage == "fly" and e.type == pygame.KEYDOWN and e.key == pygame.K_x:
            self.finish({"summary": "Docking aborted. You backed away from the station safely."}, "back")
            return True
        return super().handle_event(e)

    def update_event(self, dt):
        if self.stage != "fly":
            return
        keys = pygame.key.get_pressed()
        ax = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        ay = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        ar = keys[pygame.K_e] - keys[pygame.K_q]
        self.vx += ax * self.ACC * dt
        self.vy += ay * self.ACC * dt
        self.vang += ar * self.ROT * dt
        damp = 1 - 0.25 * dt            # a little help so it's not too hard
        self.vx *= damp
        self.vy *= damp
        self.vang *= 1 - 0.8 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.ang += self.vang * dt
        self.y = max(30, min(240, self.y))
        self.x = max(20, self.x)
        nose = self.x + self.ship.get_width() / 2
        if nose >= self.PORT[0]:
            self.contact()
        elif self.t > self.LIMIT:
            self.finish({"summary": "You ran out of time and drifted away from the station. No supplies."}, "back")

    def grade(self, key, value):
        if value <= self.GOOD[key]:
            return 2
        if value <= self.OK[key]:
            return 1
        return 0

    def contact(self):
        """GOOD on all three = perfect dock, everything at least OK = rough dock, anything worse = crash."""
        sp, off, ang = self.speed(), self.offset(), abs(self.ang)
        g = min(self.grade("speed", sp), self.grade("offset", off), self.grade("angle", ang))
        self.stage = "done"
        if g == 2:
            self.finish({"summary": "Perfect docking at %.2f m/s! The crew restocks the ship: +20%% fuel, "
                                    "+10%% energy, +15%% food." % sp,
                         "changes": {"fuel": 20, "energy": 10, "food": 15}}, "coin")
        elif g == 1:
            self.finish({"summary": "Rough docking (%.2f m/s, %.0f m off-centre, %.0f deg). The ship scraped the "
                                    "port, but you got some supplies." % (sp, off, ang),
                         "changes": {"integrity": -15, "fuel": 10, "energy": 5, "food": 8}}, "fail")
        else:
            why = []
            if self.grade("speed", sp) == 0:
                why.append("far too fast (%.2f m/s)" % sp)
            if self.grade("offset", off) == 0:
                why.append("%.0f m off the port" % off)
            if self.grade("angle", ang) == 0:
                why.append("tilted %.0f deg" % ang)
            self.finish({"fail": "CRASH! You hit the station " + ", ".join(why) + ". The collision destroyed "
                                 "the spacecraft."})

    def draw_station(self, s):
        px, py = self.PORT
        pygame.draw.rect(s, (110, 112, 130), (px + 6, py - 14, 50, 28))          # main module
        pygame.draw.rect(s, (150, 152, 170), (px + 56, py - 50, 14, 100))        # truss
        for yy in (py - 60, py + 34):                                           # solar arrays
            pygame.draw.rect(s, (40, 80, 170), (px + 40, yy, 46, 24))
            for xx in range(px + 40, px + 86, 6):
                pygame.draw.line(s, (90, 130, 210), (xx, yy), (xx, yy + 24))
        pygame.draw.rect(s, (90, 92, 110), (px, py - 8, 8, 16))                  # docking port
        pygame.draw.rect(s, YELLOW, (px - 1, py - 8, 2, 16))
        on = int(self.t * 3) % 2 == 0
        for dy in (-12, 12):
            pygame.draw.rect(s, GREEN if on else DARKGREEN, (px - 2, py + dy - 1, 3, 3))
        for xx in range(60, px - 4, 10):                                        # approach guide
            s.set_at((xx, py), (80, 90, 120))

    def draw(self, s):
        self.stars.draw(s)
        self.draw_station(s)
        if self.stage == "offer":
            ui.panel(s, (60, 40, 300, 150), fill=(14, 20, 44), border=CYAN)
            ui.text(s, "SPACE STATION IN RANGE", (210, 48), CYAN, 20, center=True)
            ui.text_block(s, "Request docking to restock the ship? A clean docking gives +20% fuel, +10% "
                             "energy and +15% food. A rough one damages the hull. Crashing ends the mission. "
                             "Flying past is always safe.", (72, 72, 276, 110), WHITE, 16)
            self.draw_buttons(s, 1 / 60)
        elif self.stage in ("fly", "done"):
            img = pygame.transform.rotate(self.ship, -self.ang)
            s.blit(img, (int(self.x) - img.get_width() // 2, int(self.y) - img.get_height() // 2))
            ui.panel(s, (4, 22, 170, 62), fill=(10, 10, 30), border=CYAN)
            rows = [("CLOSING SPEED", "%.2f m/s" % self.speed(), self.grade("speed", max(0.0, self.speed()))),
                    ("OFFSET", "%.0f m" % self.offset(), self.grade("offset", self.offset())),
                    ("ANGLE", "%+.0f deg" % self.ang, self.grade("angle", abs(self.ang))),
                    ("RANGE", "%.0f m" % max(0, self.PORT[0] - self.x - self.ship.get_width() / 2), 2)]
            for i, (k, v, gr) in enumerate(rows):
                ui.text(s, k, (10, 26 + i * 14), LIGHT, 14)
                ui.text(s, v, (168, 26 + i * 14), [RED, YELLOW, GREEN][gr], 14, right=True)
            ui.text(s, "A/D speed  W/S up-down  Q/E rotate  X abort   %.0f s" % max(0, self.LIMIT - self.t),
                    (W // 2, 254), LIGHT, 14, center=True)
        self.header(s, "SPACE STATION DOCKING", CYAN)
        self.draw_result(s)
        self.mc.draw(s)


EVENTS = {
    "docking": DockingEvent,
    "asteroid": AsteroidEvent,
    "micrometeorite": MicrometeoriteEvent,
    "malfunction": MalfunctionEvent,
    "flare": FlareEvent,
    "pirate": PirateEvent,
    "astronaut": AstronautEvent,
}


def make_event(game, mscene, kind):
    return EVENTS[kind](game, mscene)
