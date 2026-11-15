"""Science challenges. Every experiment ends with a quiz or a small mini-game.
The more science the experiment is worth, the harder the challenge (see science.TIERS).
Each challenge has 3 rounds; the number of rounds won decides the payout.

Challenges: 'quiz' (3 questions), 'calibrate' (stop the needle in the green zone),
'memory' (repeat the data stream of digits).
"""
import math
import random

import pygame

import art
import science
import ui
from scene import Scene, MissionControl
from science_questions import BANK
from settings import *

# Difficulty settings per tier
CALIBRATE = {"easy": (0.24, 0.55), "medium": (0.14, 0.85), "hard": (0.075, 1.25)}  # (zone width, sweeps/s)
MEMORY = {"easy": (3, 0.75), "medium": (5, 0.6), "hard": (7, 0.5)}               # (digits, seconds each)
NAMES = {"quiz": "SCIENCE QUIZ", "calibrate": "SENSOR CALIBRATION", "memory": "DATA STREAM RECALL"}
HOWTO = {
    "quiz": "Answer 3 questions about space science.",
    "calibrate": "Stop the moving needle inside the green zone. Press SPACE or click. 3 tries.",
    "memory": "Memorise the stream of digits, then type it back (number keys or click). 3 streams.",
}


class ScienceChallenge(Scene):
    music = "mission"

    def __init__(self, game, mscene, exp_id, stake):
        super().__init__(game)
        self.ms = game.mission
        self.mscene = mscene
        self.exp = science.EXP_BY_ID[exp_id]
        self.stake = stake
        self.tier = science.tier_for(stake)
        self.kind = random.choice(["quiz", "calibrate", "memory"])
        self.stars = art.Starfield(seed=31, decor=False)
        self.mc = MissionControl(game, (4, 196, 472, 70))
        self.t = 0.0
        self.phase = "intro"
        self.round = 0
        self.correct = 0
        self.results = []          # True/False per round
        self.feedback = None
        self.fb_t = 0.0
        self.gained = None
        self.buttons = [ui.Button((190, 176, 100, 20), "START", self.start, color=DARKGREEN, size=16,
                                  sound="select", key=pygame.K_RETURN)]
        self.mc.tip("science_challenge", [
            "Every experiment ends with a SCIENCE CHALLENGE: a quiz or a mini-game with 3 rounds.",
            "Experiments worth more science are HARDER. Win all 3 rounds for full points...",
            "...but win none and the data is corrupted - you LOSE that much science from your total!",
        ], force=bool(self.ms.level.get("tutorial")) and self.ms.turn <= 2)

    # ------------------------------------------------------------ flow
    def start(self):
        self.phase = "play"
        self.round = 0
        self.t = 0.0
        if self.kind == "quiz":
            pool = [q for q in BANK[self.tier] if q[0] not in self.ms.used_questions]
            if len(pool) < 3:
                pool = list(BANK[self.tier])
            self.questions = []
            for q, opts in random.sample(pool, 3):
                self.ms.used_questions.add(q)
                o = list(opts)
                random.shuffle(o)
                self.questions.append((q, o, o.index(opts[0])))
        self.begin_round()

    def begin_round(self):
        self.feedback = None
        self.buttons = []
        if self.kind == "quiz":
            q, opts, ans = self.questions[self.round]
            for j, opt in enumerate(opts):
                self.buttons.append(ui.Button((40, 110 + j * 23, 400, 19), opt,
                                              lambda j=j: self.answer(j == ans), color=PURPLE, size=14,
                                              tooltip=opt))
        elif self.kind == "calibrate":
            width, speed = CALIBRATE[self.tier]
            self.zone_w = width
            self.zone_c = random.uniform(0.12 + width / 2, 0.88 - width / 2)
            self.speed = speed * random.uniform(0.9, 1.15)
            self.needle_t = random.uniform(0, 1)
            self.needle = 0.0
        else:
            n, each = MEMORY[self.tier]
            self.seq = [random.randint(0, 9) for _ in range(n)]
            self.each = each
            self.entered = []
            self.show_t = 0.0
            self.mem_stage = "show"
            for d in range(10):
                x = 105 + (d % 5) * 56
                y = 120 + (d // 5) * 26
                self.buttons.append(ui.Button((x, y, 50, 22), str(d), lambda d=d: self.digit(d),
                                              color=BLUE, size=20))

    def answer(self, right):
        if self.feedback:
            return
        self.results.append(right)
        if right:
            self.correct += 1
            self.audio.play("coin")
        else:
            self.audio.play("deny")
        if self.kind == "quiz":
            q, opts, ans = self.questions[self.round]
            txt = "CORRECT!" if right else "WRONG - the answer was: " + opts[ans]
        elif self.kind == "calibrate":
            txt = "LOCKED ON!" if right else "MISSED THE ZONE"
        else:
            txt = "DATA SAVED!" if right else "WRONG - it was " + " ".join(str(d) for d in self.seq)
        self.feedback = (txt, GREEN if right else RED)
        self.fb_t = 0.0

    def digit(self, d):
        if self.kind != "memory" or self.mem_stage != "input" or self.feedback:
            return
        self.entered.append(d)
        i = len(self.entered) - 1
        if self.entered[i] != self.seq[i]:
            self.answer(False)
        elif len(self.entered) == len(self.seq):
            self.answer(True)
        else:
            self.audio.play("click")

    def finish(self):
        self.phase = "result"
        self.buttons = []
        self.gained = self.ms.finish_experiment(self.stake, self.correct)
        self.result_t = 0.0
        self.audio.play("success" if self.gained > 0 else "fail")

    # ------------------------------------------------------------ events
    def handle(self, e):
        if self.mc.handle(e):
            return True
        if self.mc.active:
            return True
        if self.phase == "result":
            if self.result_t > 0.6 and ((e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or
                                        (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN))):
                self.mscene.on_science_done(self.exp["id"], self.stake, self.gained, self.correct)
            return True
        if self.phase == "play" and not self.feedback:
            if self.kind == "calibrate":
                if (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE) or \
                        (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
                    self.answer(abs(self.needle - self.zone_c) <= self.zone_w / 2)
                    return True
            if self.kind == "memory" and e.type == pygame.KEYDOWN:
                if pygame.K_0 <= e.key <= pygame.K_9:
                    self.digit(e.key - pygame.K_0)
                    return True
                if pygame.K_KP0 <= e.key <= pygame.K_KP9:
                    self.digit(e.key - pygame.K_KP0)
                    return True
        return super().handle(e)

    def update(self, dt):
        self.mc.update(dt)
        self.stars.update(dt, 30)
        if self.mc.active:
            return
        self.t += dt
        if self.phase == "result":
            self.result_t += dt
            return
        if self.phase != "play":
            return
        if self.feedback:
            self.fb_t += dt
            if self.fb_t > 1.6:
                self.round += 1
                if self.round >= 3:
                    self.finish()
                else:
                    self.begin_round()
            return
        if self.kind == "calibrate":
            self.needle_t += dt * self.speed
            self.needle = 1.0 - abs((self.needle_t % 2.0) - 1.0)   # bounces 0..1..0
        elif self.kind == "memory" and self.mem_stage == "show":
            self.show_t += dt
            if self.show_t > self.each * len(self.seq) + 0.3:
                self.mem_stage = "input"

    # ------------------------------------------------------------ drawing
    def draw(self, s):
        self.stars.draw(s, 0.6)
        col = science.TIER_COLORS[self.tier]
        ui.panel(s, (0, 0, W, 18), fill=(10, 14, 40), border=col)
        ui.text(s, "%s - %s  |  %s  |  AT STAKE: %d SCIENCE" % (
            NAMES[self.kind], self.exp["name"].upper(), science.tier_label(self.tier), self.stake),
                (W // 2, 4), YELLOW, 14, center=True)
        if self.phase == "intro":
            self.draw_intro(s, col)
        elif self.phase == "play":
            self.draw_rounds(s)
            getattr(self, "draw_" + self.kind)(s)
            if self.feedback:
                fy = 206 if self.kind == "quiz" else 176
                ui.text(s, self.feedback[0][:80], (W // 2, fy), self.feedback[1], 16, center=True)
        else:
            self.draw_result(s)
        self.draw_buttons(s, 1 / 60)
        self.mc.draw(s)

    def draw_intro(self, s, col):
        ui.panel(s, (40, 28, 400, 172), fill=(14, 16, 44), border=col)
        ui.text(s, NAMES[self.kind], (W // 2, 36), CYAN, 20, center=True)
        ui.text(s, "DIFFICULTY: " + science.tier_label(self.tier), (W // 2, 56), col, 16, center=True)
        ui.text_block(s, HOWTO[self.kind], (56, 74, 368, 30), WHITE, 16)
        ui.text(s, "PAYOUT (rounds won out of 3)", (W // 2, 108), CYAN, 14, center=True)
        y = 122
        for c in (3, 2, 1, 0):
            f = science.payout(self.tier, c)
            if f < 0:
                txt, tc = "LOSE %d science (data corrupted)" % self.stake, RED
            else:
                txt, tc = "+%d science  (%d%%)" % (round(self.stake * f), f * 100), GREEN if f > 0 else LIGHT
            ui.text(s, "%d/3:" % c, (150, y), WHITE, 14)
            ui.text(s, txt, (186, y), tc, 14)
            y += 12
        ui.text(s, "Your science: %d / %d needed" % (self.ms.science, self.ms.level["game"]["science_needed"]),
                (W // 2, 214), LIGHT, 14, center=True)

    def draw_rounds(self, s):
        ui.text(s, "ROUND %d OF 3" % min(3, self.round + 1), (40, 26), CYAN, 16)
        for i in range(3):
            x = 400 + i * 14
            c = DARK
            if i < len(self.results):
                c = GREEN if self.results[i] else RED
            pygame.draw.rect(s, c, (x, 26, 10, 10))
            pygame.draw.rect(s, GREY, (x, 26, 10, 10), 1)

    def draw_quiz(self, s):
        q, opts, ans = self.questions[self.round]
        ui.panel(s, (30, 44, 420, 60), fill=(30, 14, 50), border=PURPLE)
        ui.text_block(s, q, (40, 50, 400, 50), WHITE, 16)

    def draw_calibrate(self, s):
        x, y, w, h = 60, 100, 360, 22
        ui.text(s, "Stop the needle in the GREEN zone! (SPACE / click)", (W // 2, 60), WHITE, 16, center=True)
        pygame.draw.rect(s, (40, 20, 30), (x, y, w, h))
        zx = x + int((self.zone_c - self.zone_w / 2) * w)
        pygame.draw.rect(s, DARKGREEN, (zx, y, int(self.zone_w * w), h))
        pygame.draw.rect(s, GREEN, (zx, y, int(self.zone_w * w), h), 1)
        for i in range(0, w + 1, 18):
            pygame.draw.line(s, GREY, (x + i, y + h), (x + i, y + h + 3))
        pygame.draw.rect(s, GREY, (x, y, w, h), 1)
        nx = x + int(self.needle * w)
        pygame.draw.rect(s, YELLOW, (nx - 1, y - 6, 3, h + 12))
        ui.text(s, "SIGNAL", (x, y - 14), CYAN, 14)

    def draw_memory(self, s):
        if self.mem_stage == "show":
            ui.text(s, "MEMORISE THE DATA STREAM!", (W // 2, 52), YELLOW, 16, center=True)
            i = int(self.show_t / self.each)
            if i < len(self.seq) and (self.show_t % self.each) < self.each * 0.75:
                ui.text(s, str(self.seq[i]), (W // 2, 72), WHITE, 24, center=True, scale=2)
                ui.text(s, "%d / %d" % (i + 1, len(self.seq)), (W // 2, 110), LIGHT, 14, center=True)
        else:
            ui.text(s, "TYPE IT BACK", (W // 2, 52), YELLOW, 16, center=True)
            n = len(self.seq)
            for i in range(n):
                bx = W // 2 - n * 15 + i * 30
                done = i < len(self.entered)
                ui.panel(s, (bx + 2, 70, 26, 26), fill=DARKGREEN if done else DARK, border=GREY)
                if done:
                    ui.text(s, str(self.entered[i]), (bx + 15, 76), WHITE, 20, center=True)

    def draw_buttons(self, s, dt):
        if self.kind == "memory" and self.phase == "play" and getattr(self, "mem_stage", "") == "show":
            return
        super().draw_buttons(s, dt)

    def draw_result(self, s):
        good = self.gained > 0
        bad = self.gained < 0
        fill = (16, 50, 30) if good else (DARKRED if bad else (40, 40, 60))
        ui.panel(s, (70, 50, 340, 120), fill=fill, border=GREEN if good else (RED if bad else GREY))
        ui.text(s, "EXPERIMENT COMPLETE" if not bad else "DATA CORRUPTED!", (W // 2, 58), YELLOW, 20, center=True)
        ui.text(s, "Rounds won: %d / 3" % self.correct, (W // 2, 82), WHITE, 16, center=True)
        if good:
            txt, c = "+%d SCIENCE" % self.gained, GREEN
        elif bad:
            txt, c = "%d SCIENCE (lost)" % self.gained, RED
        else:
            txt, c = "No science gained", LIGHT
        ui.text(s, txt, (W // 2, 100), c, 24, center=True)
        need = self.ms.level["game"]["science_needed"]
        ui.text(s, "Total science: %d / %d needed" % (self.ms.science, need), (W // 2, 128),
                GREEN if self.ms.science >= need else CYAN, 16, center=True)
        if self.result_t > 0.6:
            ui.text(s, "Click to continue", (W // 2, 150), LIGHT, 14, center=True)
