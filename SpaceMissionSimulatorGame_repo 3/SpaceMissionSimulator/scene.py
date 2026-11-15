"""Scene base class, Mission Control guide, and the friendly-alien loading screen."""
import random

import pygame

import art
import ui
from settings import *


class Scene:
    music = None

    def __init__(self, game):
        self.game = game
        self.buttons = []

    @property
    def audio(self):
        return self.game.audio

    def enter(self):
        if self.music:
            self.audio.music(self.music)

    def handle(self, e):
        for b in self.buttons:
            if b.handle(e, self.audio):
                return True
        return False

    def update(self, dt):
        pass

    def draw(self, s):
        pass

    def draw_buttons(self, s, dt):
        for b in self.buttons:
            b.draw(s, dt)
        mp = pygame.mouse.get_pos()
        for b in self.buttons:
            if b.rect.collidepoint(mp) and b.tooltip:
                ui.draw_tooltip(s, b.tooltip, mp)


class MissionControl:
    """The Mission Control guide. Tips are shown once (tracked in the save file);
    `force` tips (used during the tutorial) are always shown."""

    def __init__(self, game, rect=(4, 196, 472, 70)):
        self.game = game
        self.box = ui.DialogueBox(rect, art.character("mc", 2), "MISSION CONTROL",
                                  game.audio, color=(18, 30, 60), border=CYAN)

    @property
    def active(self):
        return self.box.active

    def tip(self, key, lines, force=False, on_done=None):
        seen = self.game.save.data["seen_tips"]
        if key in seen and not force:
            if on_done:
                on_done()
            return False
        if key not in seen:
            seen.append(key)
            self.game.save.save()
        if isinstance(lines, str):
            lines = [lines]
        name = self.game.save.data["player_name"] or "Commander"
        self.box.say([l.replace("{name}", name) for l in lines], on_done)
        return True

    def say(self, lines, on_done=None):
        if isinstance(lines, str):
            lines = [lines]
        name = self.game.save.data["player_name"] or "Commander"
        self.box.say([l.replace("{name}", name) for l in lines], on_done)

    def move(self, rect):
        self.box.rect = pygame.Rect(rect)

    def handle(self, e):
        return self.box.handle(e)

    def update(self, dt):
        self.box.update(dt)

    def draw(self, s):
        self.box.draw(s)


class FactPopup:
    """Friendly alien showing a NASA fact. Not a random event: purely educational."""

    def __init__(self, game, rect=(40, 70, 400, 120)):
        self.game = game
        self.fact = game.facts.next_fact()
        self.variant = art.pick_variant("alien")   # sometimes a different alien look
        self.rect = pygame.Rect(rect)
        self.t = 0.0
        self.done = False

    def handle(self, e):
        if self.t < 0.6:
            return True
        if (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or \
                (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN)):
            self.game.facts.learn(self.fact)
            self.game.audio.play("select")
            self.done = True
        return True

    def update(self, dt):
        self.t += dt

    def draw(self, s):
        r = self.rect
        ui.panel(s, r, fill=(16, 40, 30), border=GREEN)
        sprite = art.character("alien", 3, int(self.t * 3), self.variant)
        s.blit(sprite, (r.x + 8, r.y + 14))
        ui.text(s, "ZORP, THE FRIENDLY ALIEN", (r.x + 66, r.y + 6), GREEN, 16)
        ui.text(s, "Space fact! [%s]" % self.fact["cat"], (r.x + 66, r.y + 20), YELLOW, 14)
        ui.text_block(s, self.fact["text"], (r.x + 66, r.y + 34, r.w - 76, r.h - 50), WHITE, 16)
        if self.t > 0.6 and int(self.t * 2) % 2 == 0:
            ui.text(s, "Click to remember this fact!", (r.right - 8, r.bottom - 14), GREEN, 14, right=True)


class LoadingScene(Scene):
    """Transition screen between interfaces, hosted by the friendly alien."""

    def __init__(self, game, target, label="LOADING"):
        super().__init__(game)
        self.target = target
        self.label = label
        self.t = 0.0
        self.popup = FactPopup(game, (40, 80, 400, 120))
        self.stars = game.stars

    def handle(self, e):
        if self.t < 1.2:
            return True
        self.popup.handle(e)
        return True

    def update(self, dt):
        self.t += dt
        self.stars.update(dt, 40)
        self.popup.update(dt)
        if self.popup.done:
            self.game.switch(self.target, loading=False)

    def draw(self, s):
        self.stars.draw(s)
        ui.text(s, self.label + "." * (int(self.t * 3) % 4), (W // 2, 30), YELLOW, 24, center=True)
        p = min(1.0, self.t / 1.2)
        pygame.draw.rect(s, DARK, (140, 56, 200, 8))
        for i in range(0, int(196 * p), 6):
            pygame.draw.rect(s, YELLOW, (142 + i, 58, 4, 4))
        if self.t >= 0.3:
            self.popup.draw(s)
