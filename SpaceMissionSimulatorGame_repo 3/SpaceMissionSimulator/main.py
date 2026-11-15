"""SPACE MISSION SIMULATOR - by UWC ISAK-1
Run:  python main.py      (requires: pip install pygame)

Controls: mouse for menus. F11 toggles fullscreen. ESC goes back / pauses.
"""
import asyncio
import os
import sys

WEB = sys.platform == "emscripten"   # running in a web browser (pygbag build)

os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "0")  # nearest-neighbour scaling

import pygame

import art
import audio
import ui
from facts import FactBook
from save import SaveData
from settings import *


class Game:
    def __init__(self, headless=False):
        pygame.init()
        flags = pygame.SCALED | pygame.RESIZABLE
        self.screen = pygame.display.set_mode((W, H), flags)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.save = SaveData()
        self.facts = FactBook(self.save)
        import nasa_data
        nasa_data.start()   # fetch real solar flare data in the background (offline: built-in list)
        self.stars = art.Starfield(seed=3)
        self._show_boot("Preparing pixels...")
        audio.ensure_assets(self._show_boot)
        self.audio = audio.Audio(self.save)
        self.audio.load()
        self.scene = None
        self.running = True
        self.mission = None  # current MissionState
        self.design_mission = None  # current design.DesignMission (Design Mission mode only)
        from menu import MainMenu
        self.switch(MainMenu(self), loading=False)

    def _show_boot(self, msg):
        self.screen.fill(SPACE)
        ui.text(self.screen, "SPACE MISSION SIMULATOR", (W // 2, 110), YELLOW, 24, center=True)
        ui.text(self.screen, msg, (W // 2, 140), LIGHT, 16, center=True)
        pygame.display.flip()
        pygame.event.pump()

    def switch(self, scene, loading=False, label="LOADING"):
        """Change scene. loading=True shows the friendly-alien fact screen first."""
        if loading:
            from scene import LoadingScene
            scene = LoadingScene(self, scene, label)
        self.scene = scene
        scene.enter()

    def step(self):
        """One frame: input, update, draw."""
        dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                try:
                    pygame.display.toggle_fullscreen()
                except pygame.error:
                    pass
            else:
                self.scene.handle(e)
        self.scene.update(dt)
        self.scene.draw(self.screen)
        pygame.display.flip()

    async def run(self):
        # async so the same loop works on the desktop and in a web browser (pygbag)
        while self.running:
            self.step()
            await asyncio.sleep(0)
        self.save.save()
        if not WEB:
            pygame.quit()


async def main():
    await Game().run()


if __name__ == "__main__":
    asyncio.run(main())
    if not WEB:
        sys.exit()
