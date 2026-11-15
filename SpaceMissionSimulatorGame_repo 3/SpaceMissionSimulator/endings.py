"""Game over, mission report, black hole finale and credits."""
import math
import random

import pygame

import art
import nasa_data
import science
import ui
from levels import next_level
from scene import Scene, MissionControl
from settings import *


class GameOver(Scene):
    music = None

    def __init__(self, game):
        super().__init__(game)
        self.ms = game.mission
        self.t = 0.0
        self.buttons = [
            ui.Button((90, 236, 140, 22), "RETRY MISSION", self.retry, color=ORANGE, text_color=BLACK, size=16,
                      sound="select"),
            ui.Button((250, 236, 140, 22), "LEVEL SELECT", self.levels, color=DARK, text_color=YELLOW, size=16),
        ]

    def enter(self):
        self.audio.stop_music(300)
        self.audio.play("fail")

    def retry(self):
        from build import BuildScene
        dm = self.game.design_mission
        level = dm.vlevel if (dm and self.ms.dm) else self.ms.base_level
        self.game.switch(BuildScene(self.game, level, self.ms.design), loading=True,
                         label="BACK TO THE DRAWING BOARD")

    def levels(self):
        from levelselect import LevelSelect
        self.game.switch(LevelSelect(self.game), loading=True)

    def update(self, dt):
        self.t += dt
        self.game.stars.update(dt, 5)

    def draw(self, s):
        self.game.stars.draw(s, 0.6)
        ms = self.ms
        c = RED if int(self.t * 2) % 2 == 0 else DARKRED
        ui.text(s, "MISSION FAILED", (W // 2, 14), c, 24, center=True, scale=2)
        ui.panel(s, (40, 62, 400, 166), fill=(30, 10, 16), border=RED)
        ui.text(s, "MISSION: %s     ASTRONAUT: %s" % (ms.level["name"].upper(), self.game.save.data["player_name"]),
                (52, 70), YELLOW, 16)
        ui.text(s, "REASON FOR FAILURE:", (52, 88), ORANGE, 14)
        ui.text_block(s, ms.failed or "Unknown", (52, 100, 376, 44), WHITE, 16)
        rows = [("Turn reached", "%d / %d" % (ms.turn, ms.turns_total)),
                ("Mission day", "%.1f" % ms.day),
                ("Science", "%d / %d" % (ms.science, ms.level["game"]["science_needed"])),
                ("Energy / Food / Fuel", "%d%% / %d%% / %d%%" % (ms.pct("energy"), ms.pct("food"), ms.pct("fuel"))),
                ("Shield / Hull / Crew", "%d%% / %d%% / %d%%" % (ms.pct("shield"), ms.integrity, ms.crew)),
                ("Delta-v margin at launch", "%+d m/s" % ms.a["margin"])]
        for i, (k, v) in enumerate(rows):
            ui.text(s, k, (52, 150 + i * 12), LIGHT, 14)
            ui.text(s, v, (428, 150 + i * 12), WHITE, 14, right=True)
        self.draw_buttons(s, 1 / 60)


class MissionReport(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.ms = game.mission
        self.rows, self.total, self.passed, self.reasons = science.compute_score(self.ms)
        self.t = 0.0
        self.mc = MissionControl(game)
        sd = game.save.data
        lid = self.ms.level["id"]
        self.unlocked = None
        if self.passed:
            if lid not in sd["completed"]:
                sd["completed"].append(lid)
            nxt = next_level(lid)
            if nxt and nxt not in sd["unlocked"]:
                sd["unlocked"].append(nxt)
                self.unlocked = nxt
            sd["best_scores"][lid] = max(sd["best_scores"].get(lid, 0), self.total)
            game.save.save()
            if self.ms.level.get("tutorial"):
                self.mc.tip("tutorial_done", [
                    "Outstanding work, {name}! You've completed your training.",
                    "From now on I'll only speak up when something NEW happens. Mars is unlocked - good luck out there!",
                ])
        self.buttons = [
            ui.Button((90, 244, 140, 20), "CONTINUE", self.levels, color=GREEN, text_color=BLACK, size=16,
                      sound="select"),
            ui.Button((250, 244, 140, 20), "RETRY MISSION", self.retry, color=DARK, text_color=YELLOW, size=16),
        ]

    def levels(self):
        from levelselect import LevelSelect
        self.game.switch(LevelSelect(self.game), loading=True)

    def retry(self):
        from build import BuildScene
        self.game.switch(BuildScene(self.game, self.ms.base_level, self.ms.design), loading=True)

    def handle(self, e):
        if self.mc.handle(e):
            return True
        return super().handle(e)

    def update(self, dt):
        self.t += dt
        self.mc.update(dt)
        self.game.stars.update(dt, 8)

    def draw(self, s):
        self.game.stars.draw(s)
        ms = self.ms
        title = "MISSION SUCCESS!" if self.passed else "MISSION INCOMPLETE"
        ui.text(s, title, (W // 2, 6), GREEN if self.passed else ORANGE, 24, center=True, scale=2)
        ui.panel(s, (40, 50, 400, 190), fill=NAVY, border=GREEN if self.passed else ORANGE)
        ui.text(s, "MISSION REPORT: %s  -  %s" % (ms.level["name"].upper(), self.game.save.data["player_name"]),
                (50, 56), YELLOW, 16)
        shown = min(len(self.rows), int(self.t * 4) + 1)
        for i, (lab, val, pts) in enumerate(self.rows[:shown]):
            y = 72 + i * 12
            ui.text(s, lab, (50, y), LIGHT, 14)
            ui.text(s, val, (300, y), WHITE, 14, right=True)
            ui.text(s, "+%d" % pts, (430, y), YELLOW, 14, right=True)
        if shown >= len(self.rows):
            y = 72 + len(self.rows) * 12 + 2
            pygame.draw.line(s, YELLOW, (50, y), (430, y))
            ui.text(s, "TOTAL SCORE", (50, y + 4), YELLOW, 16)
            ui.text(s, str(self.total), (430, y + 4), YELLOW, 16, right=True)
            y += 20
            if self.passed:
                msg = "Requirements met! " + ("%s UNLOCKED!" % self.unlocked.upper() if self.unlocked else "")
                ui.text(s, msg, (W // 2, y), GREEN, 16, center=True)
            else:
                for r in self.reasons[:2]:
                    ui.text(s, "X " + r, (W // 2, y), RED, 14, center=True)
                    y += 11
            real = nasa_data.REAL_MISSIONS.get(ms.level["id"])
            if real:
                ui.text_block(s, "Your trip: %d days.  REAL MISSION: %s" % (ms.day, real), (50, 214, 380, 26),
                              CYAN, 14)
        self.draw_buttons(s, 1 / 60)
        self.mc.draw(s)


def finish_game(game):
    """Mark the black hole (and the game) as completed and save. Called by both endings."""
    sd = game.save.data
    if game.mission:
        game.mission.objective_done = True
    if "blackhole" not in sd["completed"]:
        sd["completed"].append("blackhole")
    sd["game_finished"] = True
    game.save.save()


def first_black_hole_visit(game):
    return "blackhole" not in game.save.data["completed"]


class BlackHoleChoice(Scene):
    """First arrival at the black hole: ENTER it, or TURN BACK."""
    music = "ending"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.ms = game.mission
        self.ship = pygame.transform.rotate(art.draw_ship(self.ms.design.c, flight=True), -90)
        self.stars = art.Starfield(seed=98)
        self.mc = MissionControl(game, (4, 4, 472, 62))
        self.choice_ready = False
        self.buttons = [
            ui.Button((70, 236, 160, 24), "ENTER THE BLACK HOLE", self.enter_hole, color=PURPLE, size=16,
                      sound="select"),
            ui.Button((250, 236, 160, 24), "TURN BACK", self.turn_back, color=DARKRED, size=16, sound="select"),
        ]
        self.mc.say([
            "We made it, {name}. There it is... the black hole.",
            "Nothing that crosses the event horizon can ever come back. Not even light.",
            "Our instruments could learn things no human has ever known - but only from the inside.",
            "It's your call, Commander. Go in... or turn back.",
        ], on_done=self.ready)

    def ready(self):
        self.choice_ready = True

    def enter_hole(self):
        if self.choice_ready:
            self.game.switch(BlackHoleEnding(self.game))

    def turn_back(self):
        if self.choice_ready:
            self.game.switch(TurnBackEnding(self.game))

    def handle(self, e):
        if self.mc.handle(e):
            return True
        if not self.choice_ready:
            return True
        return super().handle(e)

    def update(self, dt):
        self.t += dt
        self.stars.update(dt, 15)
        self.mc.update(dt)

    def draw(self, s):
        self.stars.draw(s)
        t = self.t
        bh = art.planet("blackhole", 46)
        s.blit(bh, (300 - bh.get_width() // 2, 140 - bh.get_height() // 2))
        for i in range(60):   # swirling particles
            a = i / 60 * 2 * math.pi + t * (1.0 + (i % 5) * 0.15)
            rr = 70 + (i % 7) * 6
            pygame.draw.rect(s, [WHITE, YELLOW, ORANGE, PINK][i % 4],
                             (int(300 + math.cos(a) * rr), int(140 + math.sin(a) * rr * 0.32), 2, 2))
        bob = int(math.sin(t * 2) * 2)
        s.blit(self.ship, (60, 140 - self.ship.get_height() // 2 + bob))
        if self.choice_ready:
            ui.text(s, "THE EVENT HORIZON", (W // 2, 210), YELLOW, 20, center=True)
            self.draw_buttons(s, 1 / 60)
        self.mc.draw(s)


class TurnBackEnding(Scene):
    """Alternate ending: the ship turns back, but power and food run out on the way."""
    music = None
    DURATION = 20.0
    MESSAGES = [
        (0.5, "Firing all engines... pulling away from the black hole."),
        (3.5, "WARNING: The engines used most of our power fighting its gravity."),
        (6.5, "POWER CRITICAL - shutting down non-essential systems."),
        (9.5, "FOOD STORES EMPTY - Earth is still years away."),
        (12.5, "Life support failing..."),
    ]

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.ms = game.mission
        self.ship = pygame.transform.rotate(art.draw_ship(self.ms.design.c, flight=True), 90)
        self.stars = art.Starfield(seed=97)
        self.energy0 = self.ms.pct("energy") if self.ms else 60
        self.food0 = self.ms.pct("food") if self.ms else 60
        self.alarm_t = 0.0
        finish_game(game)

    def enter(self):
        self.audio.stop_music(500)

    def update(self, dt):
        self.t += dt
        self.stars.update(dt, max(0.0, 40 - self.t * 4))
        self.alarm_t += dt
        if 3 < self.t < 15 and self.alarm_t > 1.0:
            self.alarm_t = 0.0
            self.audio.play("alarm")
        if self.t > self.DURATION:
            self.game.switch(Credits(self.game, "turnback"))

    def handle(self, e):
        if self.t > 3 and e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.game.switch(Credits(self.game, "turnback"))
        return True

    def draw(self, s):
        t = self.t
        self.stars.draw(s, max(0.2, 1 - t / 18))
        bh = art.planet("blackhole", 30)
        s.blit(bh, (420 - bh.get_width() // 2, 120 - bh.get_height() // 2))
        drift = min(1.0, t / 14)
        sx = int(260 - 120 * drift)
        s.blit(self.ship, (sx, 120 - self.ship.get_height() // 2 + int(math.sin(t * 9) * (1 if t > 4 else 0))))
        if 2 < t < 15 and int(t * 4) % 2 == 0:   # red alarm flash
            flash = pygame.Surface((W, H), pygame.SRCALPHA)
            flash.fill((200, 0, 0, 60))
            s.blit(flash, (0, 0))
        # draining bars
        f = max(0.0, min(1.0, (t - 3) / 10))
        energy = self.energy0 * (1 - f)
        food = self.food0 * (1 - max(0.0, min(1.0, (t - 5) / 9)))
        ui.panel(s, (130, 186, 220, 44), fill=(20, 8, 12), border=RED)
        ui.resource_bar(s, 140, 192, "energy", energy / 100, "ENERGY", t)
        ui.resource_bar(s, 140, 206, "food", food / 100, "FOOD", t)
        msg = [m for at, m in self.MESSAGES if t >= at]
        if msg:
            ui.text(s, msg[-1], (W // 2, 40), RED if int(t * 3) % 2 else ORANGE, 16, center=True)
        if t > 14:
            fade = pygame.Surface((W, H))
            fade.fill((0, 0, 0))
            fade.set_alpha(min(255, int((t - 14) / 5 * 255)))
            s.blit(fade, (0, 0))


class BlackHoleEnding(Scene):
    music = "ending"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.ms = game.mission
        self.ship = pygame.transform.rotate(art.draw_ship(self.ms.design.c, flight=True), -90)
        self.stars = art.Starfield(seed=99)
        finish_game(game)
        self.lines = [
            "Entering the wormhole...",
            "Approaching the event horizon. Time is slowing down...",
            "Tidal forces are stretching the ship...",
            "Nothing can escape now. Not even light.",
        ]

    def update(self, dt):
        self.t += dt
        self.stars.update(dt, 30 + self.t * 10)
        if self.t > 22:
            self.game.switch(Credits(self.game))

    def handle(self, e):
        if self.t > 3 and e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.game.switch(Credits(self.game))
        return True

    def draw(self, s):
        t = self.t
        dim = max(0.0, 1 - max(0.0, t - 6) / 10)
        self.stars.draw(s, dim)
        r = int(10 + t * 4.5)
        cx, cy = 300, 135
        # swirling accretion disk
        for i in range(160):
            a = i / 160 * 2 * math.pi + t * (1.5 + (i % 5) * 0.2)
            rr = r * (1.6 + (i % 7) * 0.12)
            x = cx + math.cos(a) * rr
            y = cy + math.sin(a) * rr * 0.32
            c = [WHITE, YELLOW, ORANGE, RED][i % 4]
            c = tuple(int(v * max(0.15, dim)) for v in c)
            pygame.draw.rect(s, c, (int(x), int(y), 2, 2))
        pygame.draw.circle(s, (0, 0, 0), (cx, cy), r)
        pygame.draw.circle(s, tuple(int(v * dim) for v in (255, 220, 160)), (cx, cy), r + 1, 1)
        # ship falls in and stretches (spaghettification)
        if t < 14:
            f = t / 14
            stretch = 1 + f * f * 3
            img = pygame.transform.scale(self.ship, (int(self.ship.get_width() * stretch),
                                                     max(1, int(self.ship.get_height() / (1 + f * 1.5)))))
            sx = int(40 + (cx - 60) * f * f)
            s.blit(img, (sx, cy - img.get_height() // 2))
        i = min(len(self.lines) - 1, int(t / 4))
        if t < 16:
            ui.text(s, self.lines[i], (W // 2, 230), tuple(int(v * max(0.3, dim)) for v in YELLOW), 16, center=True)
        if t > 12:
            fade = pygame.Surface((W, H))
            fade.fill((0, 0, 0))
            fade.set_alpha(min(255, int((t - 12) / 6 * 255)))
            s.blit(fade, (0, 0))


class Credits(Scene):
    music = "ending"

    def __init__(self, game, ending="enter"):
        super().__init__(game)
        self.t = 0.0
        name = game.save.data["player_name"]
        if ending == "turnback":
            story = [("Commander %s turned back from the edge of forever..." % name, LIGHT, 16),
                     ("but the journey home was too far.", LIGHT, 16)]
        else:
            story = [("Commander %s crossed the event horizon" % name, LIGHT, 16),
                     ("and became part of the universe's greatest mystery.", LIGHT, 16)]
        self.lines = [
            ("SPACE MISSION SIMULATOR", YELLOW, 24),
            ("by UWC ISAK-1", YELLOW, 16),
            ("", WHITE, 16),
        ] + story + [
            ("", WHITE, 16), ("", WHITE, 16),
            ("Special thanks to:", CYAN, 20),
            ("", WHITE, 16),
            ("Leo H and Zhamilia", WHITE, 20),
            ("- Design Team -", GREY, 16),
            ("", WHITE, 16),
            ("Madalitso, Aron and Luka", WHITE, 20),
            ("- Coding Team -", GREY, 16),
            ("", WHITE, 16), ("", WHITE, 16),
            ("Thank you for playing!", YELLOW, 20),
        ]
        self.buttons = []
        self.stars = art.Starfield(seed=5)

    def update(self, dt):
        self.t += dt
        self.stars.update(dt, 10)

    def to_levels(self):
        """Progress was saved when the ending started; go back to the destination map."""
        self.game.save.save()
        from levelselect import LevelSelect
        self.game.switch(LevelSelect(self.game), loading=True)

    def handle(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.t = max(self.t, 26)
            return True
        clicked = (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or \
                  (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN))
        if clicked:
            if self.t >= 27:
                self.to_levels()
            elif self.t > 3:
                self.t = 26    # first click skips the scroll, the next one continues
            return True
        return True

    def draw(self, s):
        if self.t < 26:
            s.fill(BLACK)
            if self.t > 3:
                self.stars.draw(s, min(1.0, (self.t - 3) / 4))
            y0 = H - (self.t - 1) * 18
            y = y0
            for txt, col, size in self.lines:
                if -20 < y < H:
                    ui.text(s, txt, (W // 2, int(y)), col, size, center=True)
                y += 18 if size < 20 else 22
            if y < H * 0.45:
                self.t = 26
        else:
            self.stars.draw(s)
            s.blit(art.planet("blackhole", 26), (W // 2 - 52, 40))
            ui.text(s, "THE END", (W // 2, 150), YELLOW, 24, center=True, scale=3)
            ui.text(s, "SPACE MISSION SIMULATOR  -  by UWC ISAK-1", (W // 2, 210), YELLOW, 16, center=True)
            if self.t >= 27 and int(self.t * 2) % 2 == 0:
                ui.text(s, "Progress saved - click to return to the destination map", (W // 2, 240), LIGHT, 14,
                        center=True)
