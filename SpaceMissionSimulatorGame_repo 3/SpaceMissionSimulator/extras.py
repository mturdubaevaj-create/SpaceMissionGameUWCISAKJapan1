"""Extra menu screens: the Fact Book (every fact Zorp has taught you) and
About & Sources (where the game's data comes from)."""
import pygame

import nasa_data
import ui
from facts import FACTS
from scene import Scene
from settings import *


class FactBook(Scene):
    music = "menu"
    PER_PAGE = 4

    def __init__(self, game, back):
        super().__init__(game)
        self.back_to = back
        self.page = 0
        known = set(game.facts.known)
        self.known = [f for f in FACTS if f["id"] in known]
        self.buttons = [
            ui.Button((10, 246, 70, 18), "< BACK", self.back, color=DARK, text_color=YELLOW, size=14, sound="back"),
            ui.Button((300, 246, 80, 18), "< PREV", lambda: self.turn(-1), color=DARK, size=14),
            ui.Button((390, 246, 80, 18), "NEXT >", lambda: self.turn(1), color=DARK, size=14),
        ]

    def pages(self):
        return max(1, (len(self.known) + self.PER_PAGE - 1) // self.PER_PAGE)

    def turn(self, d):
        self.page = (self.page + d) % self.pages()

    def back(self):
        self.game.switch(self.back_to)

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.back()
                return True
            if e.key in (pygame.K_RIGHT, pygame.K_LEFT):
                self.turn(1 if e.key == pygame.K_RIGHT else -1)
                return True
        return super().handle(e)

    def update(self, dt):
        self.game.stars.update(dt, 6)

    def draw(self, s):
        self.game.stars.draw(s, 0.6)
        ui.text(s, "FACT BOOK", (W // 2, 6), YELLOW, 24, center=True)
        ui.text(s, "Facts discovered: %d / %d   (Zorp teaches you new ones on loading screens)" % (
            len(self.known), len(FACTS)), (W // 2, 28), LIGHT, 14, center=True)
        pygame.draw.rect(s, DARK, (90, 42, 300, 5))
        pygame.draw.rect(s, GREEN, (90, 42, int(300 * len(self.known) / max(1, len(FACTS))), 5))
        if not self.known:
            ui.text_block(s, "No facts yet! Play a mission - Zorp the friendly alien shares a space fact on "
                             "every loading screen.", (60, 100, 360, 60), WHITE, 16)
        items = self.known[self.page * self.PER_PAGE:(self.page + 1) * self.PER_PAGE]
        for i, f in enumerate(items):
            y = 54 + i * 47
            ui.panel(s, (10, y, 460, 44), fill=(16, 40, 30), border=GREEN)
            ui.text(s, f["cat"].upper(), (16, y + 3), YELLOW, 14)
            ui.text_block(s, f["text"], (16, y + 14, 448, 30), WHITE, 14)
        ui.text(s, "Page %d / %d" % (self.page + 1, self.pages()), (240, 250), LIGHT, 14, center=True)
        self.draw_buttons(s, 1 / 60)


class Sources(Scene):
    music = "menu"

    def __init__(self, game, back):
        super().__init__(game)
        self.back_to = back
        self.buttons = [ui.Button((10, 246, 70, 18), "< BACK", self.back, color=DARK, text_color=YELLOW, size=14,
                                  sound="back")]

    def back(self):
        self.game.switch(self.back_to)

    def handle(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.back()
            return True
        return super().handle(e)

    def update(self, dt):
        self.game.stars.update(dt, 6)

    def draw(self, s):
        self.game.stars.draw(s, 0.5)
        ui.text(s, "ABOUT & SOURCES", (W // 2, 6), YELLOW, 24, center=True)
        y = 30
        for k, v in nasa_data.SOURCES:
            ui.text(s, k.upper(), (12, y), CYAN, 14)
            y = ui.text_block(s, v, (98, y, 372, 26), WHITE, 14) + 2
        ui.text(s, "Solar flare data in use: " + nasa_data.flare_source(), (12, y + 2), GREEN, 14)
        ui.text_block(s, nasa_data.DISCLAIMER, (12, y + 18, 456, 30), LIGHT, 14)
        ui.text_block(s, "Credits: Leo H and Zhamilia (Design), Madalitso, Aron and Luka (Coding) - UWC ISAK-1",
                      (90, 248, 380, 20), YELLOW, 14)
        self.draw_buttons(s, 1 / 60)
