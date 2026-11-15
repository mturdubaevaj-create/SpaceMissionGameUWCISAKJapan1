"""Cargo mini-games played on arrival. One per cargo type.
To add a cargo objective, subclass MiniGame and register it in MINIGAMES."""
import math
import random

import pygame

import art
import ui
from scene import Scene, MissionControl
from settings import *


class MiniGame(Scene):
    music = "mission"

    def __init__(self, game):
        super().__init__(game)
        self.ms = game.mission
        self.t = 0.0
        self.mc = MissionControl(game, (4, 196, 472, 70))
        self.tutorial = bool(self.ms.level.get("tutorial"))
        self.done = None   # ("win"/"lose", text, quality)
        self.done_t = 0.0
        self.stars = art.Starfield(seed=31, decor=False)

    def win(self, quality, text):
        if self.done:
            return
        quality = max(0.3, min(1.0, quality))
        ms = self.ms
        ms.objective_done = True
        ms.objective_quality = quality
        from spacecraft import CARGO
        pts = CARGO[ms.deploy_key]["science"] * ms.level["game"]["science_mult"] * quality
        ms.science += pts
        self.done = ("win", text + " (+%d science)" % pts, quality)
        self.audio.play("success")

    def lose(self, reason):
        if self.done:
            return
        self.ms.fail(reason)
        self.done = ("lose", reason, 0)
        self.audio.play("explosion")

    def handle(self, e):
        if self.mc.handle(e):
            return True
        if self.done:
            if self.done_t > 1.0 and ((e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or
                                      (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN))):
                self.exit()
            return True
        if self.mc.active:
            return True
        return self.handle_game(e)

    def handle_game(self, e):
        return super().handle(e)

    def exit(self):
        from endings import GameOver, MissionReport
        if self.done[0] == "lose":
            self.game.switch(GameOver(self.game))
        elif self.ms.dm:
            self.ms.dm.record(self.ms)
            self.ms.dm.after_stop(self.game, self.ms)
        else:
            self.game.switch(MissionReport(self.game))

    def update(self, dt):
        self.mc.update(dt)
        if self.done:
            self.done_t += dt
            return
        if self.mc.active:
            return
        self.t += dt
        self.update_game(dt)

    def update_game(self, dt):
        pass

    def draw_done(self, s):
        if not self.done:
            return
        win = self.done[0] == "win"
        ui.panel(s, (80, 80, 320, 80), fill=(16, 50, 30) if win else DARKRED, border=GREEN if win else RED)
        ui.text(s, "OBJECTIVE COMPLETE!" if win else "MISSION FAILED", (W // 2, 88), YELLOW, 20, center=True)
        ui.text_block(s, self.done[1], (90, 108, 300, 36), WHITE, 14)
        if self.done_t > 1.0:
            ui.text(s, "Click to continue", (W // 2, 146), LIGHT, 14, center=True)


# ------------------------------------------------------------------ lander
class LandingGame(MiniGame):
    def __init__(self, game):
        super().__init__(game)
        g = self.ms.level["game"]["landing_g"]
        self.g = g
        self.thrust_acc = max(0.6, 2.6 * g) if g > 0.5 else 0.6
        self.x, self.y = 70.0, 30.0
        self.vx, self.vy = 9.0, 2.0
        self.angle = -20.0          # degrees, 0 = upright
        self.fuel = 100.0
        self.fuel_rate = 9.0 if self.tutorial else 11.0
        self.thrusting = False
        self.boom = None
        rnd = random.Random()
        self.terrain = []
        self.pads = []
        pad_x = [rnd.randint(200, 280), rnd.randint(360, 420)]
        h = 220
        x = 0
        while x <= W:
            on_pad = any(px <= x <= px + 36 for px in pad_x)
            if not on_pad:
                h += rnd.randint(-12, 12)
                h = max(170, min(250, h))
            self.terrain.append((x, h))
            for px in pad_x:
                if px <= x < px + 6 and not any(p[0] == px for p in self.pads):
                    self.pads.append((px, 36, h))
            x += 6
        self.max_vy = 3.5 if self.tutorial else 2.5
        self.mc.tip("landing", [
            "LANDING! Fly the lander down to a flat landing pad (the ones with lights).",
            "LEFT/RIGHT rotate. UP or SPACE fires the main engine in the direction the lander points.",
            "Touch down UPRIGHT (under 12 deg), slowly (under %.1f m/s down, 2 m/s sideways). Fuel is limited!" % self.max_vy,
        ], force=self.tutorial)

    def ground_at(self, x):
        for i in range(len(self.terrain) - 1):
            x0, h0 = self.terrain[i]
            x1, h1 = self.terrain[i + 1]
            if x0 <= x <= x1:
                return h0 + (h1 - h0) * (x - x0) / max(1, x1 - x0)
        return self.terrain[-1][1]

    def update_game(self, dt):
        if self.boom is not None:
            self.boom += dt
            return
        keys = pygame.key.get_pressed()
        rot = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            rot -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            rot += 1
        self.angle = max(-90, min(90, self.angle + rot * 90 * dt))
        self.thrusting = (keys[pygame.K_UP] or keys[pygame.K_SPACE] or keys[pygame.K_w]) and self.fuel > 0
        ax, ay = 0.0, self.g
        if self.thrusting:
            rad = math.radians(self.angle)
            ax += math.sin(rad) * self.thrust_acc
            ay -= math.cos(rad) * self.thrust_acc
            self.fuel = max(0.0, self.fuel - self.fuel_rate * dt)
            if int(self.t * 10) % 3 == 0:
                self.audio.play("thrust")
        self.vx += ax * dt
        self.vy += ay * dt
        self.x += self.vx * dt * 3      # 1 m = 1/3 px horizontally... (world scale)
        self.y += self.vy * dt * 3
        if self.x < 0:
            self.x += W
        if self.x > W:
            self.x -= W
        self.y = max(-40, self.y)
        gy = self.ground_at(self.x)
        if self.y + 7 >= gy:
            self.touchdown()

    def touchdown(self):
        pad = next((p for p in self.pads if p[0] <= self.x - 4 and self.x + 4 <= p[0] + p[1]), None)
        problems = []
        if abs(self.vy) > self.max_vy:
            problems.append("too fast (%.1f m/s)" % self.vy)
        if abs(self.vx) > 2.0:
            problems.append("drifting sideways (%.1f m/s)" % self.vx)
        if abs(self.angle) > 12:
            problems.append("tilted %d deg" % abs(self.angle))
        if pad is None:
            problems.append("missed the flat landing pad")
        if problems:
            self.boom = 0.0
            self.y = self.ground_at(self.x) - 7
            self.lose("The lander crashed: " + ", ".join(problems) + ".")
        else:
            soft = 1 - abs(self.vy) / self.max_vy
            centre = 1 - abs(self.x - (pad[0] + pad[1] / 2)) / (pad[1] / 2)
            q = 0.5 + 0.25 * soft + 0.15 * centre + 0.1 * (self.fuel / 100)
            speed = abs(self.vy)
            self.vy = self.vx = 0
            self.y = self.ground_at(self.x) - 7
            self.win(q, "The Eagle has landed! Touchdown at %.1f m/s with %d%% fuel left." % (speed, self.fuel))
            self.audio.play("coin")

    def draw(self, s):
        self.stars.draw(s)
        lid = self.ms.level["id"]
        if lid == "moon":
            s.blit(art.planet("earth", 14), (380, 20))
        elif lid == "mars":
            s.fill((150, 90, 70), (0, 0, W, 140), special_flags=pygame.BLEND_MIN)
        col = {"moon": (150, 150, 160), "mars": (170, 80, 50), "asteroid": (90, 80, 70)}.get(lid, (130, 120, 110))
        pts = [(0, H)] + self.terrain + [(W, H)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.lines(s, tuple(min(255, c + 40) for c in col), False, self.terrain, 1)
        for px, pw, ph in self.pads:
            pygame.draw.rect(s, (90, 90, 100), (px, ph, pw, 3))
            if int(self.t * 3) % 2 == 0:
                s.set_at((px, ph - 1), GREEN)
                s.set_at((px + pw - 1, ph - 1), GREEN)
        # lander (your image if images/lander.png exists, otherwise the original drawing)
        custom = None
        if self.boom is None or self.done and self.done[0] == "win":
            custom = art.fit_image("lander.png", 20, 16)
            if custom is not None:
                # 32x32 canvas so the lander's centre stays the rotation point; feet at +8 px
                lander = pygame.Surface((32, 32), pygame.SRCALPHA)
                lander.blit(custom, (16 - custom.get_width() // 2, 24 - custom.get_height()))
                if self.thrusting and int(self.t * 20) % 2 == 0:
                    pygame.draw.rect(lander, ORANGE, (14, 24, 4, 5))
                    pygame.draw.rect(lander, YELLOW, (15, 24, 2, 3))
                img = pygame.transform.rotate(lander, -self.angle)
                s.blit(img, (int(self.x) - img.get_width() // 2, int(self.y) - img.get_height() // 2))
        if custom is None and (self.boom is None or self.done and self.done[0] == "win"):
            lander = pygame.Surface((14, 16), pygame.SRCALPHA)
            pygame.draw.rect(lander, GOLD, (3, 2, 8, 7))
            pygame.draw.rect(lander, LIGHT, (4, 0, 6, 3))
            pygame.draw.rect(lander, (40, 40, 70), (5, 1, 2, 1))
            pygame.draw.line(lander, LIGHT, (3, 9), (0, 15))
            pygame.draw.line(lander, LIGHT, (10, 9), (13, 15))
            pygame.draw.rect(lander, GREY, (5, 9, 4, 3))
            if self.thrusting and int(self.t * 20) % 2 == 0:
                pygame.draw.rect(lander, ORANGE, (5, 12, 4, 4))
                pygame.draw.rect(lander, YELLOW, (6, 12, 2, 2))
            img = pygame.transform.rotate(lander, -self.angle)
            s.blit(img, (int(self.x) - img.get_width() // 2, int(self.y) - img.get_height() // 2))
        if not (self.boom is None or self.done and self.done[0] == "win"):
            art.explosion(s, self.x, self.y, min(1.0, self.boom / 1.5))
        # HUD
        alt = max(0.0, (self.ground_at(self.x) - self.y - 7) / 3)
        ui.panel(s, (4, 4, 150, 66), fill=(10, 10, 30), border=CYAN)
        rows = [("ALTITUDE", "%.0f m" % alt, True),
                ("DESCENT", "%.1f m/s" % self.vy, abs(self.vy) <= self.max_vy),
                ("SIDEWAYS", "%.1f m/s" % self.vx, abs(self.vx) <= 2.0),
                ("TILT", "%d deg" % self.angle, abs(self.angle) <= 12)]
        for i, (k, v, ok) in enumerate(rows):
            ui.text(s, k, (10, 8 + i * 11), LIGHT, 14)
            ui.text(s, v, (148, 8 + i * 11), GREEN if ok else RED, 14, right=True)
        ui.text(s, "FUEL", (10, 54), ORANGE, 14)
        pygame.draw.rect(s, DARK, (40, 55, 108, 7))
        pygame.draw.rect(s, ORANGE if self.fuel > 20 else RED, (40, 55, int(108 * self.fuel / 100), 7))
        ui.text(s, "g = %.2f m/s^2" % self.g, (W - 6, 6), WHITE, 14, right=True)
        self.draw_done(s)
        self.mc.draw(s)


# ------------------------------------------------------------------ rover
class RoverGame(MiniGame):
    LENGTH = 1400

    def __init__(self, game):
        super().__init__(game)
        rnd = random.Random()
        self.x = 20.0
        self.v = 0.0
        self.cam = 0.0
        self.battery = 100.0
        self.samples = []
        for i in range(5):
            self.samples.append([150 + i * 250 + rnd.randint(-40, 40), 0.0, False])
        self.rocks = [rnd.randint(120, self.LENGTH - 80) for _ in range(9)]
        self.hits = 0
        self.hit_cd = 0.0
        self.mc.tip("rover", [
            "ROVER DEPLOYED! Drive with LEFT/RIGHT. Big rocks: slow down below 2 m/s to crawl over them!",
            "Stop next to a glowing sample and HOLD SPACE to drill it. Collect at least 3 and reach the flag before the battery dies.",
        ])

    def ground(self, x):
        return 210 + 10 * math.sin(x / 70.0) + 5 * math.sin(x / 23.0)

    def update_game(self, dt):
        keys = pygame.key.get_pressed()
        acc = 0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            acc = 3
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            acc = -3
        else:
            self.v *= 0.96
        self.v = max(-3, min(6, self.v + acc * dt))
        self.x = max(0, self.x + self.v * dt * 12)
        self.battery -= (abs(self.v) * 0.25 + 0.4) * dt
        self.hit_cd = max(0, self.hit_cd - dt)
        for r in self.rocks:
            if abs(self.x - r) < 8 and self.hit_cd <= 0 and abs(self.v) > 2.0:
                self.hits += 1
                self.hit_cd = 1.2
                self.v = -1.5
                self.audio.play("hit")
                if self.hits >= 3:
                    self.lose("The rover broke a wheel on the rocks and got stuck forever.")
                    return
        drilling = keys[pygame.K_SPACE]
        for smp in self.samples:
            if not smp[2] and abs(self.x - smp[0]) < 10 and abs(self.v) < 0.8 and drilling:
                smp[1] += dt
                self.battery -= dt * 0.8
                if int(self.t * 10) % 3 == 0:
                    self.audio.play("click")
                if smp[1] >= 1.2:
                    smp[2] = True
                    self.audio.play("science")
        self.cam = max(0, min(self.LENGTH - W, self.x - 120))
        got = sum(1 for s in self.samples if s[2])
        if self.battery <= 0:
            if got >= 3:
                self.win(got / 5, "Battery flat, but %d samples were sent home!" % got)
            else:
                self.lose("The rover's battery died with only %d/3 samples collected." % got)
        if self.x >= self.LENGTH - 30:
            if got >= 3:
                self.win(0.4 + got / 8, "Rover reached the target crater with %d samples!" % got)
            else:
                self.lose("Reached the crater with only %d/3 samples - not enough science." % got)

    def draw(self, s):
        lid = self.ms.level["id"]
        s.fill((190, 120, 90) if lid == "mars" else (14, 12, 24))
        if lid != "mars":
            self.stars.draw(s)
        col = (170, 80, 50) if lid == "mars" else (100, 90, 80)
        pts = [(0, H)]
        for sx in range(0, W + 4, 4):
            pts.append((sx, self.ground(sx + self.cam)))
        pts.append((W, H))
        pygame.draw.polygon(s, col, pts)
        for r in self.rocks:
            rx = r - self.cam
            if -10 < rx < W + 10:
                pygame.draw.rect(s, (70, 50, 40), (rx - 5, self.ground(r) - 8, 10, 8))
        for smp in self.samples:
            sx = smp[0] - self.cam
            if -10 < sx < W + 10:
                c = GREEN if smp[2] else (CYAN if int(self.t * 4) % 2 else WHITE)
                pygame.draw.rect(s, c, (sx - 2, self.ground(smp[0]) - 4, 4, 4))
                if 0 < smp[1] < 1.2:
                    pygame.draw.rect(s, YELLOW, (sx - 6, self.ground(smp[0]) - 12, int(12 * smp[1] / 1.2), 2))
        fx = self.LENGTH - 30 - self.cam
        pygame.draw.line(s, WHITE, (fx, self.ground(self.LENGTH - 30)), (fx, self.ground(self.LENGTH - 30) - 20))
        pygame.draw.rect(s, RED, (fx, self.ground(self.LENGTH - 30) - 20, 8, 5))
        rx = self.x - self.cam
        gy = self.ground(self.x)
        rover = art.fit_image("rover.png", 22, 22)
        if rover is not None:
            s.blit(rover, (int(rx) - rover.get_width() // 2, int(gy) - 2 - rover.get_height()))
        else:
            self.draw_rover(s, rx, gy)
        self.draw_hud(s)

    def draw_rover(self, s, rx, gy):
        pygame.draw.rect(s, (230, 230, 236), (rx - 8, gy - 12, 16, 6))
        pygame.draw.rect(s, GOLD, (rx - 3, gy - 18, 6, 6))
        pygame.draw.line(s, GREY, (rx + 4, gy - 18), (rx + 6, gy - 22))
        for wx in (-7, 0, 6):
            pygame.draw.rect(s, (30, 30, 30), (rx + wx - 1, gy - 6, 3, 3))

    def draw_hud(self, s):
        got = sum(1 for x in self.samples if x[2])
        ui.panel(s, (4, 4, 220, 30), fill=(10, 10, 30), border=CYAN)
        ui.text(s, "SAMPLES %d/5 (need 3)  HITS %d/3  SPEED %.1f" % (got, self.hits, self.v), (10, 8), WHITE, 14)
        ui.text(s, "BATTERY", (10, 20), YELLOW, 14)
        pygame.draw.rect(s, YELLOW, (60, 21, int(150 * max(0, self.battery) / 100), 6))
        self.draw_done(s)
        self.mc.draw(s)


# ------------------------------------------------------------------ satellite
class OrbitGame(MiniGame):
    def __init__(self, game):
        super().__init__(game)
        self.phase_ang = math.pi
        self.burns = 0
        self.misses = 0
        self.sat_fuel = 100.0
        self.ecc = [0.62, 0.4, 0.15]
        self.window = 0.32
        self.mc.tip("orbit", [
            "SATELLITE ORBIT INSERTION! Your satellite swings around the planet on a stretched orbit.",
            "Press SPACE when it passes through the GREEN burn window (closest point, periapsis). 3 good burns = circular orbit!",
        ])

    def orbit_pos(self, ang, e):
        rp = 46.0
        a = rp / (1 - e)
        r = a * (1 - e * e) / (1 + e * math.cos(ang))
        return 230 + r * math.cos(ang), 115 + r * math.sin(ang) * 0.6

    def handle_game(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
            ang = (self.phase_ang + math.pi) % (2 * math.pi) - math.pi
            if abs(ang) < self.window:
                self.burns += 1
                self.audio.play("thrust")
                self.audio.play("coin")
                if self.burns >= 3:
                    self.win(1.0 - 0.15 * self.misses, "Satellite in a stable circular orbit after %d misses." % self.misses)
            else:
                self.misses += 1
                self.sat_fuel -= 22
                self.audio.play("deny")
                if self.sat_fuel <= 0:
                    self.lose("The satellite wasted its fuel on badly-timed burns and drifted away.")
            return True
        return False

    def update_game(self, dt):
        e = self.ecc[min(self.burns, 2)]
        r_factor = (1 + e * math.cos(self.phase_ang)) ** 2  # faster near periapsis (Kepler's 2nd law)
        self.phase_ang += dt * 0.9 * r_factor / (1 + e)
        self.phase_ang %= 2 * math.pi

    def draw(self, s):
        self.stars.draw(s)
        lid = self.ms.level["icon"]
        e = self.ecc[min(self.burns, 2)] if self.burns < 3 else 0.0
        pts = [self.orbit_pos(a / 40 * 2 * math.pi, e) for a in range(41)]
        pygame.draw.lines(s, GREY, False, [(int(x), int(y)) for x, y in pts], 1)
        p = art.planet(lid, 26)
        s.blit(p, (230 - p.get_width() // 2, 115 - p.get_height() // 2))
        wp = [self.orbit_pos(a, e) for a in (-self.window, -self.window / 2, 0, self.window / 2, self.window)]
        pygame.draw.lines(s, GREEN, False, [(int(x), int(y)) for x, y in wp], 3)
        sx, sy = self.orbit_pos(self.phase_ang, e)
        sat = art.fit_image("satellite.png", 28, 28)
        if sat is not None:
            # the dish points up-left (135 deg) in the picture: turn it to face the planet
            face = math.degrees(math.atan2(-(115 - sy), 230 - sx))
            img = pygame.transform.rotate(sat, face - 135)
            s.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() // 2))
        else:
            pygame.draw.rect(s, GOLD, (int(sx) - 2, int(sy) - 2, 5, 5))
            pygame.draw.line(s, (60, 100, 200), (int(sx) - 6, int(sy)), (int(sx) + 6, int(sy)))
        ui.panel(s, (4, 4, 200, 30), fill=(10, 10, 30), border=CYAN)
        ui.text(s, "BURNS %d/3   MISSES %d" % (self.burns, self.misses), (10, 8), WHITE, 14)
        ui.text(s, "SAT FUEL %d%%" % max(0, self.sat_fuel), (10, 20), ORANGE, 14)
        ui.text(s, "SPACE = burn", (W - 6, 6), LIGHT, 14, right=True)
        self.draw_done(s)
        self.mc.draw(s)


# ------------------------------------------------------------------ telescope
class TelescopeGame(MiniGame):
    LIMIT = 40.0

    def __init__(self, game):
        super().__init__(game)
        self.cx, self.cy = 240.0, 135.0
        self.locks = 0
        self.hold = 0.0
        self.new_target()
        self.mc.tip("telescope", [
            "TELESCOPE CALIBRATION! Move the crosshair with the ARROW keys or mouse onto the target star.",
            "Hold it steady inside the ring to lock on. Lock 3 targets in 40 seconds!",
        ])

    def new_target(self):
        self.tx, self.ty = random.uniform(80, 400), random.uniform(50, 180)
        self.tvx, self.tvy = random.uniform(-25, 25), random.uniform(-15, 15)
        self.hold = 0.0

    def update_game(self, dt):
        keys = pygame.key.get_pressed()
        mv = 120 * dt
        moved = False
        if keys[pygame.K_LEFT]:
            self.cx -= mv; moved = True
        if keys[pygame.K_RIGHT]:
            self.cx += mv; moved = True
        if keys[pygame.K_UP]:
            self.cy -= mv; moved = True
        if keys[pygame.K_DOWN]:
            self.cy += mv; moved = True
        if not moved and pygame.mouse.get_focused():
            mx, my = pygame.mouse.get_pos()
            self.cx += (mx - self.cx) * min(1, dt * 4)
            self.cy += (my - self.cy) * min(1, dt * 4)
        self.tx += self.tvx * dt + math.sin(self.t * 3) * 0.3
        self.ty += self.tvy * dt
        if not 40 < self.tx < 440:
            self.tvx *= -1
        if not 30 < self.ty < 185:
            self.tvy *= -1
        if math.hypot(self.cx - self.tx, self.cy - self.ty) < 8:
            self.hold += dt
            if self.hold >= 2.0:
                self.locks += 1
                self.audio.play("science")
                if self.locks >= 3:
                    self.win(1.0 - self.t / (self.LIMIT * 2), "All 3 targets calibrated! First images are stunning.")
                    return
                self.new_target()
        else:
            self.hold = max(0.0, self.hold - dt * 0.5)
        if self.t > self.LIMIT:
            if self.locks >= 2:
                self.win(0.55, "Calibrated %d targets - good enough to start observing." % self.locks)
            else:
                self.lose("The telescope could not be calibrated (%d/3 locks)." % self.locks)

    def draw(self, s):
        self.stars.draw(s)
        if self.ms.level["id"] == "sun":
            s.blit(art.planet("sun", 40), (-30, 150))
        pygame.draw.circle(s, YELLOW, (int(self.tx), int(self.ty)), 2)
        pygame.draw.circle(s, (255, 255, 200), (int(self.tx), int(self.ty)), 4, 1)
        c = GREEN if self.hold > 0 else RED
        pygame.draw.circle(s, c, (int(self.cx), int(self.cy)), 8, 1)
        pygame.draw.line(s, c, (int(self.cx) - 12, int(self.cy)), (int(self.cx) + 12, int(self.cy)))
        pygame.draw.line(s, c, (int(self.cx), int(self.cy) - 12), (int(self.cx), int(self.cy) + 12))
        ui.panel(s, (4, 4, 220, 30), fill=(10, 10, 30), border=CYAN)
        ui.text(s, "LOCKS %d/3   TIME %d s" % (self.locks, max(0, self.LIMIT - self.t)), (10, 8), WHITE, 14)
        pygame.draw.rect(s, GREEN, (10, 21, int(100 * min(1, self.hold / 2.0)), 6))
        self.draw_done(s)
        self.mc.draw(s)


# ------------------------------------------------------------------ lab
class LabGame(MiniGame):
    COLORS = [RED, GREEN, BLUE, YELLOW]

    def __init__(self, game):
        super().__init__(game)
        self.round = 0
        self.mistakes = 0
        self.pads = [pygame.Rect(150 + (i % 2) * 94, 40 + (i // 2) * 74, 86, 66) for i in range(4)]
        self.start_round()
        self.mc.tip("lab", [
            "LAB OPERATIONS! Watch which experiment chambers light up, then click them in the same order.",
        ])

    def start_round(self):
        self.seq = [random.randrange(4) for _ in range(3 + self.round)]
        self.entered = []
        self.show_t = 0.0
        self.showing = True

    def handle_game(self, e):
        if self.showing or e.type != pygame.MOUSEBUTTONDOWN:
            return False
        for i, r in enumerate(self.pads):
            if r.collidepoint(e.pos):
                self.entered.append(i)
                if self.seq[len(self.entered) - 1] != i:
                    self.mistakes += 1
                    self.audio.play("deny")
                    if self.mistakes >= 3:
                        self.lose("Too many lab errors - the experiments were ruined.")
                    else:
                        self.start_round()
                else:
                    self.audio.play("click")
                    if len(self.entered) == len(self.seq):
                        self.round += 1
                        self.audio.play("science")
                        if self.round >= 3:
                            self.win(1 - 0.2 * self.mistakes, "All lab experiments completed!")
                        else:
                            self.start_round()
                return True
        return False

    def update_game(self, dt):
        if self.showing:
            self.show_t += dt
            if self.show_t > 0.6 * len(self.seq) + 0.4:
                self.showing = False

    def draw(self, s):
        s.fill((20, 22, 36))
        lit = None
        if self.showing:
            i = int(self.show_t / 0.6)
            if i < len(self.seq) and self.show_t % 0.6 < 0.45:
                lit = self.seq[i]
        for i, r in enumerate(self.pads):
            c = self.COLORS[i] if lit == i else tuple(v // 3 for v in self.COLORS[i])
            ui.panel(s, r, fill=c, border=LIGHT)
        ui.text(s, "ROUND %d/3   MISTAKES %d/3   %s" % (self.round + 1, self.mistakes,
                                                    "WATCH..." if self.showing else "YOUR TURN"), (W // 2, 8), WHITE, 16,
                center=True)
        self.draw_done(s)
        self.mc.draw(s)


MINIGAMES = {"lander": LandingGame, "rover": RoverGame, "satellite": OrbitGame,
             "telescope": TelescopeGame, "lab": LabGame}


def make_minigame(game):
    return MINIGAMES[game.mission.deploy_key](game)
