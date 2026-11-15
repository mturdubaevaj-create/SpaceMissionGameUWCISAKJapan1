"""Main menu, settings and player setup screens."""
import math

import pygame

import art
import ui
from scene import Scene
from settings import *


class MainMenu(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        bw = 120
        x = W // 2 - bw // 2
        self.buttons = [
            ui.Button((x, 154, bw, 18), "START", self.start, color=DARK, text_color=YELLOW,
                      size=18, sound="select", key=pygame.K_RETURN),
            ui.Button((x, 176, bw, 18), "FACT BOOK", self.factbook, color=DARK, text_color=YELLOW, size=18),
            ui.Button((x, 198, bw, 18), "ABOUT & SOURCES", self.sources, color=DARK, text_color=YELLOW, size=16),
            ui.Button((x, 220, bw, 18), "SETTINGS", self.settings, color=DARK, text_color=YELLOW, size=18),
            ui.Button((x, 242, bw, 18), "EXIT", self.quit, color=DARK, text_color=YELLOW, size=18),
        ]
        self.ship_x = -40

    def start(self):
        self.game.switch(PlayerSetup(self.game))

    def settings(self):
        self.game.switch(SettingsScene(self.game, self))

    def factbook(self):
        from extras import FactBook
        self.game.switch(FactBook(self.game, self))

    def sources(self):
        from extras import Sources
        self.game.switch(Sources(self.game, self))

    def quit(self):
        self.game.running = False

    def update(self, dt):
        self.t += dt
        self.game.stars.update(dt, 12)
        self.ship_x += dt * 30
        if self.ship_x > W + 60:
            self.ship_x = -60

    def draw(self, s):
        self.game.stars.draw(s)
        s.blit(art.planet("saturn", 18), (392, 120))
        s.blit(art.planet("mars", 9), (40, 120))
        s.blit(art.planet("moon", 26), (20, 190))
        s.blit(art.planet("jupiter", 14), (400, 190))
        ship = pygame.transform.rotate(art.draw_ship(
            {"ship": "heavy", "engine": "liquid", "energy": "solar", "cargo": "satellite",
             "shield": "cork"}, flight=True), -90)
        sy = 140 + int(math.sin(self.t * 2) * 3)
        s.blit(ship, (int(self.ship_x), sy))
        if int(self.t * 12) % 2 == 0:
            pygame.draw.rect(s, ORANGE, (int(self.ship_x) + 2, sy + 38, 6, 4))
        # big chunky yellow title (rendered small then scaled with nearest-neighbour)
        bob = int(math.sin(self.t * 1.6) * 2)
        ui.text(s, "SPACE MISSION", (W // 2, 40 + bob), YELLOW, 20, center=True, scale=3)
        ui.text(s, "SIMULATOR", (W // 2, 86 + bob), YELLOW, 20, center=True, scale=3)
        ui.text(s, "by UWC ISAK-1", (W // 2, 136), YELLOW, 16, center=True, scale=1)
        self.draw_buttons(s, 1 / 60)
        ui.text(s, "F11: fullscreen", (W - 4, H - 12), YELLOW, 14, right=True)


class SettingsScene(Scene):
    music = "menu"

    def __init__(self, game, back_to):
        super().__init__(game)
        self.back_to = back_to
        sd = game.save.data
        self.sliders = [
            ui.Slider((150, 90, 180, 8), sd["music_volume"], self.set_music, "MUSIC VOLUME"),
            ui.Slider((150, 135, 180, 8), sd["sfx_volume"], self.set_sfx, "SOUND EFFECTS VOLUME"),
        ]
        self.confirm = False
        self.buttons = [
            ui.Button((150, 170, 180, 18), "RESET PROGRESS", self.reset, color=DARKRED,
                      text_color=YELLOW, size=16),
            ui.Button((190, 220, 100, 20), "BACK", self.back, color=DARK, text_color=YELLOW,
                      size=18, sound="back", key=pygame.K_ESCAPE),
        ]

    def set_music(self, v):
        self.game.save.data["music_volume"] = v
        self.audio.apply_volume()

    def set_sfx(self, v):
        self.game.save.data["sfx_volume"] = v
        self.audio.apply_volume()
        self.audio.play("click")

    def reset(self):
        if not self.confirm:
            self.confirm = True
            self.buttons[0].label = "CLICK AGAIN TO CONFIRM"
        else:
            self.game.save.reset_progress()
            self.buttons[0].label = "PROGRESS RESET!"
            self.confirm = False

    def back(self):
        self.game.save.save()
        self.game.switch(self.back_to)

    def handle(self, e):
        for sl in self.sliders:
            sl.handle(e)
        return super().handle(e)

    def update(self, dt):
        self.game.stars.update(dt, 8)

    def draw(self, s):
        self.game.stars.draw(s)
        ui.panel(s, (110, 30, 260, 220), fill=NAVY, border=YELLOW)
        ui.text(s, "SETTINGS", (W // 2, 42), YELLOW, 20, center=True, scale=2)
        for sl in self.sliders:
            sl.draw(s)
        self.draw_buttons(s, 1 / 60)


class PlayerSetup(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.input = ui.TextInput((140, 120, 200, 26), game.save.data["player_name"])
        self.t = 0.0
        self.error = ""
        self.buttons = [
            ui.Button((190, 165, 100, 20), "CONTINUE", self.go, color=GREEN, text_color=BLACK,
                      size=18, sound="select"),
            ui.Button((10, 245, 60, 18), "BACK", self.back, color=DARK, text_color=YELLOW,
                      sound="back", key=pygame.K_ESCAPE),
        ]

    def go(self):
        name = self.input.value.strip()
        if not name:
            self.error = "Enter a name, astronaut!"
            self.audio.play("deny")
            return
        self.game.save["player_name"] = name
        from levelselect import LevelSelect
        self.game.switch(LevelSelect(self.game), loading=True)

    def back(self):
        self.game.switch(MainMenu(self.game))

    def handle(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.go()
            return True
        if self.input.handle(e):
            self.audio.play("type")
            self.error = ""
            return True
        return super().handle(e)

    def update(self, dt):
        self.t += dt
        self.game.stars.update(dt, 10)

    def draw(self, s):
        self.game.stars.draw(s)
        ui.panel(s, (100, 40, 280, 160), fill=NAVY, border=YELLOW)
        ui.text(s, "ASTRONAUT REGISTRATION", (W // 2, 52), YELLOW, 18, center=True)
        s.blit(art.character("player", 2), (W // 2 - 16, 72))
        ui.text(s, "Type your name and press ENTER", (W // 2, 106), LIGHT, 14, center=True)
        self.input.draw(s, 1 / 60)
        if self.error:
            ui.text(s, self.error, (W // 2, 150), RED, 14, center=True)
        self.draw_buttons(s, 1 / 60)
