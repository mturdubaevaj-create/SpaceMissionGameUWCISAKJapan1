"""Destination selection map and mission briefing."""
import math

import pygame

import art
import ui
from levels import LEVELS, LEVEL_BY_ID, ORDER
from scene import Scene, MissionControl
from settings import *
from spacecraft import CARGO


def is_unlocked(save, lid):
    if lid == "blackhole":
        return all(l in save.data["completed"] for l in ORDER if l != "blackhole")
    return lid in save.data["unlocked"]


class LevelSelect(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.selected = None
        self.slots = []
        for i, lv in enumerate(LEVELS):
            col, row = i % 4, i // 4
            r = pygame.Rect(30 + col * 108, 50 + row * 92, 96, 82)
            self.slots.append((r, lv))
        import design
        self.design_open = design.is_unlocked(game.save)
        self.buttons = [ui.Button((6, 250, 70, 16), "MENU", self.menu, color=DARK,
                                  text_color=YELLOW, size=14, sound="back"),
                        ui.Button((150, 240, 180, 22), "DESIGN MISSION" if self.design_open else "DESIGN MISSION (LOCKED)",
                                  self.open_design, color=PURPLE if self.design_open else DARK, size=16,
                                  sound="select", tooltip=None if self.design_open else
                                  "Complete Saturn to unlock: plan your own multi-stop mission!")]
        self.brief_buttons = []
        self.mc = MissionControl(game)
        self.mc.tip("levelselect", [
            "Welcome to Mission Control, {name}! I'm your flight director.",
            "This is the destination map. Every target starts LOCKED except the Moon.",
            "The Moon is your training mission. Click the Moon to see its mission briefing!",
        ])

    def open_design(self):
        if not self.design_open:
            self.audio.play("deny")
            self.mc.say("DESIGN MISSION unlocks after you complete Saturn.")
            return
        import design
        self.game.switch(design.DesignPlanner(self.game), loading=True, label="MISSION PLANNING")

    def menu(self):
        from menu import MainMenu
        self.game.switch(MainMenu(self.game))

    def open_brief(self, lv):
        self.selected = lv
        self.audio.play("select")
        self.brief_buttons = [
            ui.Button((300, 232, 120, 20), "BUILD SHIP >", self.build, color=GREEN,
                      text_color=BLACK, size=16, sound="select"),
            ui.Button((60, 232, 80, 20), "BACK", self.close_brief, color=DARK, text_color=YELLOW,
                      sound="back", key=pygame.K_ESCAPE),
        ]
        if lv["id"] == "moon":
            self.mc.tip("briefing", [
                "A mission briefing shows REAL facts about the destination (left) and the GAME rules for this mission (right).",
                "Note the budget and the delta-v the spacecraft must deliver. When ready, press BUILD SHIP.",
            ])

    def close_brief(self):
        self.selected = None

    def build(self):
        self.game.design_mission = None
        from build import BuildScene
        self.game.switch(BuildScene(self.game, self.selected), loading=True, label="TO THE LAUNCH PAD")

    def handle(self, e):
        if self.mc.handle(e):
            return True
        if self.selected:
            for b in self.brief_buttons:
                if b.handle(e, self.audio):
                    return True
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, lv in self.slots:
                if r.collidepoint(e.pos):
                    if is_unlocked(self.game.save, lv["id"]):
                        self.open_brief(lv)
                    else:
                        self.audio.play("deny")
                        msg = "Complete EVERY other mission to unlock the Black Hole." \
                            if lv["id"] == "blackhole" else "Locked! Complete the previous mission first."
                        self.mc.say(msg)
                    return True
        return super().handle(e)

    def update(self, dt):
        self.t += dt
        self.game.stars.update(dt, 6)
        self.mc.update(dt)

    def draw(self, s):
        self.game.stars.draw(s)
        sd = self.game.save.data
        ui.text(s, "CHOOSE YOUR DESTINATION", (W // 2, 8), YELLOW, 20, center=True, scale=1)
        ui.text(s, "Astronaut: %s   Missions complete: %d/8" % (sd["player_name"], len(sd["completed"])),
                (W // 2, 28), LIGHT, 14, center=True)
        mp = pygame.mouse.get_pos()
        for r, lv in self.slots:
            unlocked = is_unlocked(self.game.save, lv["id"])
            done = lv["id"] in sd["completed"]
            hover = r.collidepoint(mp) and not self.selected
            ui.panel(s, r, fill=(30, 30, 70) if hover else NAVY,
                     border=YELLOW if (unlocked and hover) else (GREEN if done else GREY))
            ic = art.planet(lv["icon"], 16)
            bob = int(math.sin(self.t * 2 + r.x) * 2) if unlocked else 0
            s.blit(ic, (r.centerx - ic.get_width() // 2, r.y + 30 - ic.get_height() // 2 + bob))
            ui.text(s, lv["name"].upper(), (r.centerx, r.bottom - 26), WHITE if unlocked else GREY, 14, center=True)
            if not unlocked:
                dim = pygame.Surface((r.w - 4, r.h - 4), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 130))
                s.blit(dim, (r.x + 2, r.y + 2))
                self._lock(s, r.centerx, r.y + 24)
                ui.text(s, "LOCKED", (r.centerx, r.bottom - 13), RED, 14, center=True)
            elif done:
                ui.text(s, "COMPLETE", (r.centerx, r.bottom - 13), GREEN, 14, center=True)
                best = sd["best_scores"].get(lv["id"])
                if best:
                    ui.text(s, str(best), (r.right - 4, r.y + 3), YELLOW, 14, right=True)
            else:
                label = "TUTORIAL" if lv.get("tutorial") else ("FINAL" if lv.get("final") else "READY")
                ui.text(s, label, (r.centerx, r.bottom - 13), YELLOW, 14, center=True)
        self.draw_buttons(s, 1 / 60)
        if self.selected:
            self.draw_brief(s)
        self.mc.draw(s)

    def _lock(self, s, x, y):
        pygame.draw.rect(s, GOLD, (x - 6, y, 12, 9))
        pygame.draw.rect(s, GOLD, (x - 4, y - 6, 8, 7), 2)
        pygame.draw.rect(s, BLACK, (x - 1, y + 3, 2, 3))

    def draw_brief(self, s):
        lv = self.selected
        ui.panel(s, (10, 8, 460, 254), fill=(14, 16, 40), border=YELLOW)
        s.blit(art.planet(lv["icon"], 22), (20, 14))
        ui.text(s, "MISSION BRIEFING: " + lv["name"].upper(), (80, 16), YELLOW, 20)
        ui.text_block(s, "OBJECTIVE: " + lv["objective"], (80, 34, 380, 26), WHITE, 16)
        y = 66
        ui.text(s, "REAL-WORLD DATA", (18, y), CYAN, 16)
        y += 14
        labels = [("Surface temp", "temp"), ("Gravity", "gravity"), ("Escape velocity", "escape"),
                  ("Atmosphere", "atmosphere"), ("Distance", "distance"), ("Hazards", "hazards")]
        for lab, k in labels:
            ui.text(s, lab + ":", (18, y), LIGHT, 14)
            y = ui.text_block(s, lv["real"][k], (92, y, 150, 30), WHITE, 14)
            y += 2
        g = lv["game"]
        x, y = 256, 66
        ui.text(s, "GAME MISSION RULES", (x, y), ORANGE, 16)
        y += 14
        rows = [
            ("Budget", "$%dM" % g["budget"]),
            ("Delta-v after orbit", "%.1f km/s" % (g["transfer_dv"] / 1000)),
            ("Trip length", "%d days, %d turns" % (g["days"], g["turns"])),
            ("Cargo allowed", ", ".join(CARGO[c]["name"] for c in g["allowed_cargo"])),
            ("Science needed", str(g["science_needed"]) if g["science_needed"] else "-"),
            ("Entry heat rating", str(g["entry_heat"]) if g["entry_heat"] else "No atmosphere entry"),
        ]
        for lab, val in rows:
            ui.text(s, lab + ":", (x, y), LIGHT, 14)
            y = ui.text_block(s, val, (x + 92, y, 116, 30), WHITE, 14)
            y += 1
        ui.text_block(s, "Note: " + g["dv_note"], (x, y + 2, 206, 30), GREY, 14)
        for b in self.brief_buttons:
            b.draw(s, 1 / 60)
