"""Trajectory selection: between building the ship and launching it, the player
picks one of two routes (see routes.py). The map shows both routes as red dotted
lines from Earth to the destination; the cards show what each route needs from
the ship the player just built."""
import math

import pygame

import art
import ui
from mission import MissionState, route_preview, route_preview_continue, PRECISE_ENERGY
from routes import ROUTES, ORDER
from scene import Scene, MissionControl
from settings import *

EARTH = (52, 92)
DEST = (424, 88)


def bezier(p0, p1, p2, t):
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
    return x, y


# control points: the safe route loops wide, the direct one cuts straight through
CONTROL = {"safe": (238, -16), "direct": (238, 112)}


def path_points(rid, n=200):
    return [bezier(EARTH, CONTROL[rid], DEST, i / n) for i in range(n + 1)]


class TrajectoryScene(Scene):
    music = "mission"

    def __init__(self, game, level, design):
        super().__init__(game)
        self.level = level
        self.design = design.copy()
        self.tutorial = bool(level.get("tutorial"))
        self.t = 0.0
        self.selected = None
        self.stars = art.Starfield(seed=7, decor=False)
        self.mc = MissionControl(game, (4, 150, 472, 70))
        dm = game.design_mission
        self.continuing = bool(dm and level.get("design_leg") and dm.index > 0 and game.mission)
        if self.continuing:
            self.info = {rid: route_preview_continue(game.mission, level, rid) for rid in ORDER}
        else:
            self.info = {rid: route_preview(self.design, level, rid) for rid in ORDER}
        self.paths = {rid: path_points(rid) for rid in ORDER}
        self.cards = {"safe": pygame.Rect(4, 146, 234, 94), "direct": pygame.Rect(242, 146, 234, 94)}
        self.buttons = [
            ui.Button((4, 246, 110, 20), "< BACK TO BUILD", self.back, color=DARK, size=14, sound="back"),
            ui.Button((330, 244, 146, 24), "CONFIRM & GO" if self.continuing else "CONFIRM & LAUNCH",
                      self.confirm, color=RED, size=16, sound="select", enabled=False),
        ]
        self.confirm_btn = self.buttons[1]
        if self.continuing:
            self.buttons.pop(0)
        # hazard markers along the direct route (and a couple near the safe one)
        self.hazards = []
        for i, t in enumerate((0.3, 0.45, 0.58, 0.72)):
            x, y = bezier(EARTH, CONTROL["direct"], DEST, t)
            self.hazards.append(("rock" if i % 2 == 0 else "flare", x + (6 if i % 2 else -4), y + (-12 if i % 2 else 10)))
        x, y = bezier(EARTH, CONTROL["safe"], DEST, 0.62)
        self.hazards.append(("rock", x + 8, y - 10))
        self.mc.tip("trajectory_intro", [
            "Choose your TRAJECTORY - the path your spacecraft will fly from Earth to %s." % level["name"],
            "Route 1, SAFE: loops around the danger zones, so fewer random events. But it is much longer: "
            "more food, more power and MORE FUEL.",
            "Route 2, DIRECT: fast and cheap on fuel, food and power - but straight through asteroid zones "
            "and solar activity.",
            "Check each card against the ship you built. If fuel is tight, PRECISE BURNS in flight can save "
            "propellant (but they cost energy).",
        ], force=self.tutorial)

    # ------------------------------------------------------------ actions
    def back(self):
        from build import BuildScene
        dm = self.game.design_mission
        if dm and self.level.get("design_leg"):
            self.game.switch(BuildScene(self.game, dm.vlevel, self.design))
            return
        self.game.switch(BuildScene(self.game, self.level, self.design))

    def confirm(self):
        if not self.selected:
            return
        from launch import LaunchPadScene
        if self.continuing:
            from mission import MissionScene
            self.game.mission.start_leg(self.level, self.selected)
            self.game.switch(MissionScene(self.game), loading=True, label="TO %s" % self.level["name"].upper())
            return
        self.game.mission = MissionState(self.game, self.level, self.design, self.selected)
        self.game.switch(LaunchPadScene(self.game))

    def select(self, rid):
        self.selected = rid
        self.confirm_btn.enabled = True
        self.audio.play("select")

    # ------------------------------------------------------------ assessment
    def verdict(self, rid):
        """(colour, text, details) - how well the current design suits this route."""
        i = self.info[rid]
        lines = []
        bad = warn = False
        if i["sail"]:
            ok = i["dv_have"] >= i["dv_need"]
            lines.append(("Solar sail push: %s" % ("enough" if ok else "TOO WEAK"), GREEN if ok else RED))
            bad |= not ok
        else:
            have = i["fuel_after_orbit"]
            std, pre = i["fuel_std"], i["fuel_precise"]
            if std <= have:
                c = GREEN
            elif pre <= have:
                c, warn = ORANGE, True
            else:
                c, bad = RED, True
            lines.append(("Fuel: needs %d%% of tanks (%d%% precise)" % (std, pre), c))
        if i["days"] <= i["food"]:
            c = GREEN
        elif i["days"] * 0.7 <= i["food"]:
            c, warn = ORANGE, True
        else:
            c, bad = RED, True
        lines.append(("Food: %d days needed, %d stored" % (i["days"], i["food"]), c))
        if i["power_end"] >= 15:
            c, txt = GREEN, "Power: enough for the trip"
        elif i["power_end_eco"] >= 25:
            c, warn, txt = ORANGE, True, "Power: tight - plan to use ECO mode"
        else:
            c, bad, txt = RED, True, "Power: batteries will run flat"
        lines.append((txt, c))
        if bad:
            return RED, "RISKY: this ship probably can't make it", lines
        if warn:
            return ORANGE, "TIGHT: needs careful adjustments in flight", lines
        return GREEN, "This ship can make it", lines

    # ------------------------------------------------------------ events
    def handle(self, e):
        if self.mc.handle(e):
            return True
        if self.mc.active:
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for rid, r in self.cards.items():
                if r.collidepoint(e.pos):
                    self.select(rid)
                    return True
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_1, pygame.K_2):
            self.select(ORDER[e.key - pygame.K_1])
            return True
        return super().handle(e)

    def update(self, dt):
        self.t += dt
        self.stars.update(dt, 10)
        self.mc.update(dt)

    # ------------------------------------------------------------ drawing
    def draw_path(self, s, rid):
        pts = self.paths[rid]
        sel = self.selected == rid
        hov = self.cards[rid].collidepoint(pygame.mouse.get_pos())
        col = RED if (sel or hov or not self.selected) else DARKRED
        offset = int(self.t * 30) % 8 if sel else 0
        for i in range(offset, len(pts), 8):
            x, y = pts[i]
            pygame.draw.rect(s, col, (int(x) - 1, int(y) - 1, 3 if sel else 2, 3 if sel else 2))
        if sel:   # little ship travelling along the selected route
            k = int((self.t * 0.25 % 1.0) * (len(pts) - 1))
            x, y = pts[k]
            pygame.draw.rect(s, YELLOW, (int(x) - 2, int(y) - 2, 5, 5))
            pygame.draw.rect(s, WHITE, (int(x) - 1, int(y) - 1, 3, 3))
        lx, ly = pts[len(pts) // 2]
        info = ROUTES[rid]
        label = "%d: %s" % (info["num"], info["name"])
        if rid == "direct":
            label += " (through the danger zones)"
        ui.text(s, label, (int(lx), int(ly) + (-14 if rid == "safe" else 30)), YELLOW if sel else LIGHT, 14,
                center=True)

    def draw(self, s):
        self.stars.draw(s, 0.8)
        ui.panel(s, (0, 0, W, 18), fill=(10, 10, 28), border=RED)
        frm = self.level.get("from_name", "Earth").upper()
        leg = self.level.get("leg")
        title = "CHOOSE YOUR TRAJECTORY  -  %s TO %s" % (frm, self.level["name"].upper())
        if leg:
            title = "LEG %d/%d: %s TO %s" % (leg[0], leg[1], frm, self.level["name"].upper())
        ui.text(s, title, (W // 2, 4), YELLOW, 16, center=True)
        if self.level.get("assist_note"):
            ui.text(s, "BONUS: " + self.level["assist_note"], (W // 2, 20), GREEN, 14, center=True)
        # danger zone shading around the direct route
        zone = pygame.Surface((W, H), pygame.SRCALPHA)
        for kind, x, y in self.hazards[:4]:
            pygame.draw.circle(zone, (200, 40, 40, 34), (int(x), int(y)), 22)
        s.blit(zone, (0, 0))
        for kind, x, y in self.hazards:
            if kind == "rock":
                rock = art.planet("asteroid", 3)
                s.blit(rock, (int(x) - rock.get_width() // 2, int(y) - rock.get_height() // 2))
                s.blit(rock, (int(x) + 5 - rock.get_width() // 2, int(y) + 4 - rock.get_height() // 2))
            else:
                c = YELLOW if int(self.t * 4) % 2 else ORANGE
                pygame.draw.polygon(s, c, [(x, y - 5), (x + 3, y), (x - 1, y), (x + 2, y + 6), (x - 3, y - 1),
                                           (x + 1, y - 1)])
        for rid in ORDER:
            if rid != self.selected:
                self.draw_path(s, rid)
        if self.selected:
            self.draw_path(s, self.selected)
        earth = art.planet(self.level.get("from_icon", "earth"), 16)
        s.blit(earth, (EARTH[0] - earth.get_width() // 2, EARTH[1] - earth.get_height() // 2))
        ui.text(s, self.level.get("from_name", "Earth").upper(), (EARTH[0], EARTH[1] + 22), CYAN, 14,
                center=True)
        dest = art.planet(self.level["icon"], 18)
        s.blit(dest, (DEST[0] - dest.get_width() // 2, DEST[1] - dest.get_height() // 2))
        ui.text(s, self.level["name"].upper(), (DEST[0], DEST[1] + 24), ORANGE, 14, center=True)
        for rid in ORDER:
            self.draw_card(s, rid)
        self.draw_buttons(s, 1 / 60)
        if not self.selected:
            ui.text(s, "Click a route card (or press 1 / 2)", (222, 252), LIGHT, 14, center=True)
        self.mc.draw(s)

    def draw_card(self, s, rid):
        r = self.cards[rid]
        info = ROUTES[rid]
        pv = self.info[rid]
        g = pv["level"]["game"]
        sel = self.selected == rid
        hov = r.collidepoint(pygame.mouse.get_pos())
        ui.panel(s, r, fill=(40, 20, 30) if sel else ((26, 26, 60) if hov else (16, 16, 40)),
                 border=YELLOW if sel else (RED if hov else GREY))
        ui.text(s, "%d. %s" % (info["num"], info["name"]), (r.x + 6, r.y + 4), YELLOW if sel else WHITE, 16)
        danger = "LOW" if rid == "safe" else "HIGH"
        dcol = GREEN if rid == "safe" else RED
        ui.text(s, "DANGER: " + danger, (r.right - 6, r.y + 5), dcol, 14, right=True)
        ui.text(s, "Trip %d days, %d turns   Events ~%d%%/turn" % (pv["days"], pv["turns"],
                                                                  g["event_chance"] * 100),
                (r.x + 6, r.y + 20), LIGHT, 14)
        col, verdict, lines = self.verdict(rid)
        y = r.y + 33
        for txt, c in lines:
            ui.text(s, txt, (r.x + 6, y), c, 14)
            y += 11
        ui.text(s, verdict, (r.x + 6, r.bottom - 14), col, 14)
