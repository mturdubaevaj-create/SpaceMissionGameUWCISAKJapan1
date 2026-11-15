"""Spacecraft construction interface."""
import math

import pygame

import advice
import art
import physics
import ui
from scene import Scene, MissionControl
from settings import *
from spacecraft import (STEPS, TABLES, Design, LV_SIZES, MATERIALS, BOOSTERS, SHIPS,
                        SHIELDS, ENGINES, ENERGY, CARGO, component_cost)

SECTION_TITLES = {"lv_size": "SIZE", "material": "MATERIAL", "booster": "LAUNCH VEHICLE ENGINES",
                  "engine": "SPACECRAFT ENGINE", "ship": "SPACECRAFT TYPE", "shield": "HEAT SHIELD",
                  "energy": "POWER GENERATION", "cargo": "CARGO / PAYLOAD"}

TUTORIAL_STEP_TIPS = {
    "lv": ["STEP 1: The LAUNCH VEHICLE is the booster that lifts everything off Earth.",
           "Pick a SIZE, then a MATERIAL. Bigger = more fuel but heavier and pricier. Hover any option for details.",
           "Careful: aluminium is light and cheap, but its heat resistance is poor!"],
    "ship": ["STEP 2: Choose your SPACECRAFT - the part that flies to the Moon after the booster drops away.",
             "Shuttles are cheap and light. Heavy ships carry lots of fuel. Long-range ships carry years of food."],
    "shield": ["STEP 3: HEAT SHIELD. Leaving the atmosphere heats the rocket by friction.",
               "Your HEAT rating = 40% launch vehicle material + 60% shield. Ascent needs at least 45!"],
    "engines": ["STEP 4: PROPULSION. First the launch vehicle engines, then the spacecraft engine.",
                "Watch THRUST: thrust must beat the rocket's weight (TWR above 1.15) or it never leaves the pad.",
                "Isp measures efficiency. Higher Isp = more delta-v from the same fuel (rocket equation!)."],
    "energy": ["STEP 5: POWER keeps life support running. If energy hits zero, life support starts failing!",
               "Solar is cheap near the Sun. Fuel cells are strong but run out. Nuclear works anywhere."],
    "cargo": ["STEP 6: CARGO. For the Moon tutorial we need a LANDER - you will fly it down yourself!"],
}

GENERAL_TIPS = {
    "lv": "Choose a launch vehicle size and material.",
    "ship": "Choose your spacecraft type.",
    "shield": "Choose a heat shield.",
    "engines": "Choose the launch vehicle engines and the spacecraft engine.",
    "energy": "Choose a power system.",
    "cargo": "Choose the cargo for this mission.",
}


def option_summary(key, c):
    if key == "lv_size":
        return "Fuel %dt  Thrust %dkN" % (c["fuel"], c["thrust"])
    if key == "material":
        return "Mass x%.2f Heat %d Str %d" % (c["mass"], c["heat"], c["strength"])
    if key == "booster":
        return "Thrust x%.2g  Isp %d-%ds" % (c["thrust"], c["isp_sl"], c["isp_vac"])
    if key == "engine":
        if c["isp"] == 0:
            return "No fuel. Mass %.1ft" % c["mass"]
        return "%gkN Isp %ds %.1ft" % (c["thrust"], c["isp"], c["mass"])
    if key == "ship":
        return "%dt Fuel %dt Food %dd Bay %dt" % (c["dry"], c["fuel"], c["food_days"], c["cargo_cap"])
    if key == "shield":
        return "Heat %d  Durability %d  %.1ft" % (c["heat"], c["durability"], c["mass"])
    if key == "energy":
        return "Output %g  Store %d  %.1ft" % (c["output"], c["storage"], c["mass"])
    if key == "cargo":
        return "%.1ft  Science %d  Power %g" % (c["mass"], c["science"], c["energy"])
    return ""


class BuildScene(Scene):
    music = "mission"

    def __init__(self, game, level, design=None):
        super().__init__(game)
        self.level = level
        self.tutorial = bool(level.get("tutorial"))
        self.design = design.copy() if design else Design()
        self.budget = level["game"]["budget"]
        self.step = 0
        self.t = 0.0
        self.mc = MissionControl(game, (254, 20, 222, 74))
        self.tabs = []
        for i, (sid, title, keys) in enumerate(STEPS):
            short = ["LV", "SHIP", "SHLD", "PROP", "PWR", "CRGO"][i]
            self.tabs.append(ui.Button((4 + i * 41, 18, 40, 14), "%d.%s" % (i + 1, short),
                                       lambda i=i: self.goto(i), color=DARK, size=14))
        self.launch_btn = ui.Button((390, 238, 84, 26), "LAUNCH!", self.launch, color=RED,
                                    text_color=WHITE, size=20, sound="select")
        self.back_btn = ui.Button((4, 2, 44, 13), "< MAP", self.back, color=DARK, text_color=YELLOW,
                                  size=14, sound="back")
        self.why_btn = ui.Button((334, 250, 52, 14), "WHY?", self.open_why, color=ORANGE,
                                 text_color=BLACK, size=14,
                                 tooltip="Explain what causes this problem and which parts affect it.")
        self.why_open = False
        self.why_page = 0
        self.why_buttons = [
            ui.Button((14, 186, 60, 14), "< PREV", lambda: self.why_turn(-1), color=DARK, size=14),
            ui.Button((406, 186, 60, 14), "NEXT >", lambda: self.why_turn(1), color=DARK, size=14),
            ui.Button((205, 186, 70, 14), "GOT IT", self.close_why, color=DARKGREEN, size=14, sound="back"),
        ]
        self.warned_complete = False
        self.cards = []
        self.flash = 0.0
        self.message = ""
        self.mc.tip("build_intro", [
            "This is the VEHICLE ASSEMBLY BUILDING. Left: parts. Right: the launch pad.",
            "The bar at the bottom shows your rocket's stats. Every choice matters - a bad design WILL fail!",
        ], force=self.tutorial and not self.design.complete())
        self.goto(0, quiet=True)

    # ------------------------------------------------------------- navigation
    def goto(self, i, quiet=False):
        self.step = i
        sid = STEPS[i][0]
        if self.tutorial:
            if "build_%s" % sid not in self.game.save.data["seen_tips"]:
                self.mc.tip("build_%s" % sid, TUTORIAL_STEP_TIPS[sid])
        elif not quiet:
            pass
        self.build_cards()

    def back(self):
        if self.level.get("design"):
            import design
            self.game.switch(design.DesignPlanner(self.game))
            return
        from levelselect import LevelSelect
        self.game.switch(LevelSelect(self.game))

    # ------------------------------------------------------------- options
    def availability(self, key, choice):
        """(enabled, reason)"""
        if self.tutorial and key in ("engine", "booster") and choice not in ("solid", "liquid"):
            return False, "Locked in the tutorial. Only solid and liquid propulsion."
        if key == "ship" and SHIPS[choice].get("design_only") and not self.level.get("design"):
            return False, "Only available in DESIGN MISSION."
        if key == "cargo":
            if choice == "multi":
                if not self.level.get("design") or "multi" not in self.level["game"]["allowed_cargo"]:
                    return False, "Only for multi-stop Design Missions."
                if self.design["ship"] and self.design["ship"] != "station":
                    return False, "Only the Interplanetary Station has a multi-payload bay."
            elif self.design["ship"] == "station" and "multi" in self.level["game"]["allowed_cargo"]:
                return False, "The station carries the multi-payload bay (one payload per stop)."
            if choice not in self.level["game"]["allowed_cargo"]:
                return False, "Not useful for this mission's objective."
            ship = self.design["ship"]
            if ship and CARGO[choice]["mass"] > SHIPS[ship]["cargo_cap"]:
                return False, "Too heavy for this spacecraft's cargo bay."
        if self.design.cost_with(key, choice) > self.budget + 1e-6 and self.design[key] != choice:
            return False, "Over budget!"
        return True, ""

    def build_cards(self):
        self.cards = []
        sid, title, keys = STEPS[self.step]
        hidden = set()
        if not self.level.get("design"):
            hidden = {("ship", "station"), ("cargo", "multi")}
        total = sum(1 for k in keys for c in TABLES[k] if (k, c) not in hidden)
        h = min(28, int((168 - 11 * len(keys)) / total))
        y = 35
        for key in keys:
            y += 10
            for choice, c in TABLES[key].items():
                if (key, choice) in hidden:
                    continue
                r = pygame.Rect(6, y, 242, h - 2)
                self.cards.append((r, key, choice, c, (title, y)))
                y += h
            y += 2

    def choose(self, key, choice):
        ok, why = self.availability(key, choice)
        if not ok:
            self.audio.play("deny")
            self.message = why
            self.flash = 2.0
            return
        self.audio.play("select")
        self.design[key] = choice
        # keep the design consistent
        if key == "ship" and self.design["cargo"]:
            if CARGO[self.design["cargo"]]["mass"] > SHIPS[choice]["cargo_cap"]:
                self.design["cargo"] = None
                self.message = "Cargo removed: too heavy for this ship."
                self.flash = 2.0
        if self.design.total_cost() > self.budget:
            # e.g. a pricier LV material: undo
            self.design[key] = None
            self.audio.play("deny")
            self.message = "Over budget!"
            self.flash = 2.0
            return
        self.message = ""
        sid, title, keys = STEPS[self.step]
        if all(self.design[k] for k in keys):
            nxt = next((i for i, (s, t, ks) in enumerate(STEPS) if not all(self.design[k] for k in ks)), None)
            if nxt is not None and nxt != self.step:
                self.goto(nxt)
            elif self.design.complete():
                if self.tutorial:
                    self.mc.tip("build_done", [
                        "Your spacecraft is complete! Check the stats bar and WARNINGS before launch.",
                        "If something looks wrong, click a numbered tab to change that part. When ready, hit the red LAUNCH button to choose your route!"],
                                force=True)
                else:
                    self.mc.tip("build_done_general", "Spacecraft complete. Check the warnings, then LAUNCH.")

    def launch(self):
        if not self.design.complete():
            self.audio.play("deny")
            return
        from trajectory import TrajectoryScene
        dm = self.game.design_mission
        if self.level.get("design") and dm:
            dm.begin(self.design)
            self.game.switch(TrajectoryScene(self.game, dm.leg(0), self.design))
            return
        self.game.switch(TrajectoryScene(self.game, self.level, self.design))

    # ------------------------------------------------------------- WHY? help
    def problems(self):
        st = self.partial_stats()
        return self.warnings(st["analysis"]), st["analysis"]

    def open_why(self):
        if self.problems()[0]:
            self.why_open = True
            self.why_page = 0

    def close_why(self):
        self.why_open = False

    def why_turn(self, d):
        n = len(self.problems()[0])
        if n:
            self.why_page = (self.why_page + d) % n

    def draw_why(self, s):
        probs, a = self.problems()
        if not probs:
            self.why_open = False
            return
        self.why_page %= len(probs)
        stage, reason = probs[self.why_page]
        title, physics_txt, affects = advice.HELP[stage]
        ui.panel(s, (6, 36, 468, 170), fill=(16, 18, 46), border=ORANGE)
        ui.text(s, "PROBLEM %d OF %d:  %s" % (self.why_page + 1, len(probs), title), (14, 41), ORANGE, 16)
        ui.text(s, advice.numbers(stage, a, self.level), (14, 57), YELLOW, 14)
        ui.text(s, "WHAT IS GOING ON", (14, 72), CYAN, 14)
        y = ui.text_block(s, physics_txt, (14, 82, 452, 44), WHITE, 14)
        ui.text(s, "WHAT AFFECTS IT", (14, y + 3), CYAN, 14)
        ui.text_block(s, affects, (14, y + 13, 452, 176 - y), WHITE, 14)
        for b in self.why_buttons:
            if b.label == "GOT IT" or len(probs) > 1:
                b.draw(s)

    # ------------------------------------------------------------- events
    def handle(self, e):
        if self.mc.handle(e):
            return True
        if self.why_open:
            for b in self.why_buttons:
                if b.handle(e, self.audio):
                    return True
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.why_open = False
            return True
        if self.design.complete() and self.problems()[0] and self.why_btn.handle(e, self.audio):
            return True
        if self.back_btn.handle(e, self.audio):
            return True
        for b in self.tabs:
            if b.handle(e, self.audio):
                return True
        if self.design.complete() and self.launch_btn.handle(e, self.audio):
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, key, choice, c, _ in self.cards:
                if r.collidepoint(e.pos):
                    self.choose(key, choice)
                    return True
        return False

    def update(self, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.mc.update(dt)

    # ------------------------------------------------------------- stats
    def partial_stats(self):
        d = self.design
        st = {}
        mass = 0.0
        if d["lv_size"]:
            sz = LV_SIZES[d["lv_size"]]
            mm = MATERIALS[d["material"]]["mass"] if d["material"] else 1.0
            mass += sz["structure"] * mm + sz["fuel"]
            if d["booster"]:
                mass += sz["engine_mass"] * BOOSTERS[d["booster"]]["mass"]
        if d["ship"]:
            sh = SHIPS[d["ship"]]
            ff = ENGINES[d["engine"]]["fuel_factor"] if d["engine"] else 1.0
            mass += sh["dry"] + sh["fuel"] * ff
            if d["shield"]:
                mass += SHIELDS[d["shield"]]["mass"] * sh["area"]
        for k in ("engine", "energy", "cargo"):
            if d[k]:
                mass += TABLES[k][d[k]]["mass"]
        st["mass"] = mass
        heats = []
        if d["material"]:
            heats.append((0.4, MATERIALS[d["material"]]["heat"]))
        if d["shield"]:
            heats.append((0.6, SHIELDS[d["shield"]]["heat"]))
        st["heat"] = sum(w * v for w, v in heats) / sum(w for w, v in heats) if heats else None
        strs = []
        if d["material"]:
            strs.append(MATERIALS[d["material"]]["strength"])
        if d["ship"]:
            strs.append(SHIPS[d["ship"]]["strength"])
        st["strength"] = sum(strs) / len(strs) if strs else None
        st["thrust"] = LV_SIZES[d["lv_size"]]["thrust"] * BOOSTERS[d["booster"]]["thrust"] \
            if d["lv_size"] and d["booster"] else None
        st["energy"] = None
        if d["energy"]:
            en = ENERGY[d["energy"]]
            load = (SHIPS[d["ship"]]["load"] if d["ship"] else 0) + \
                   (CARGO[d["cargo"]]["energy"] if d["cargo"] else 0) + \
                   (ENGINES[d["engine"]]["power"] if d["engine"] else 0)
            st["energy"] = physics.generation(en, self.level["game"], 0, self.level["game"]["turns"]) - load
        st["cargo_cap"] = SHIPS[d["ship"]]["cargo_cap"] if d["ship"] else None
        st["cargo_mass"] = CARGO[d["cargo"]]["mass"] if d["cargo"] else 0
        st["analysis"] = physics.analyze(d.c, self.level) if d.complete() else None
        return st

    def warnings(self, a):
        w = []
        if a is None:
            return w
        fails = physics.predicted_failures(a)
        for stage, reason in fails:
            if self.tutorial or stage in ("liftoff", "fuel", "food", "orbit", "escape"):
                w.append((stage, reason))
        if not fails and a["margin"] < 400:
            w.append(("thin", "Delta-v margin is very thin (%d m/s)" % a["margin"]))
        return w

    # ------------------------------------------------------------- drawing
    def draw(self, s):
        s.fill((14, 14, 34))
        lvname = self.level["name"].upper()
        ui.text(s, "BUILD YOUR SPACECRAFT - " + lvname, (54, 3), YELLOW, 16)
        cost = self.design.total_cost()
        left = self.budget - cost
        ui.text(s, "BUDGET $%dM  LEFT $%dM" % (self.budget, left), (476, 3), GREEN if left >= 0 else RED, 16, right=True)
        self.back_btn.draw(s)
        for i, b in enumerate(self.tabs):
            keys = STEPS[i][2]
            b.selected = i == self.step
            b.color = DARKGREEN if all(self.design[k] for k in keys) else DARK
            b.draw(s)
        self.draw_options(s)
        self.draw_pad(s)
        self.draw_stats(s)
        if self.why_open:
            self.draw_why(s)
        self.mc.draw(s)
        mp = pygame.mouse.get_pos()
        if self.why_open:
            return
        for r, key, choice, c, _ in self.cards:
            if r.collidepoint(mp):
                ok, why = self.availability(key, choice)
                tip = c["desc"] + "  (" + option_summary(key, c) + ")" + (("  [" + why + "]") if not ok else "")
                tip += "  " + advice.AFFECTS[key]
                ui.draw_tooltip(s, tip, mp)
        if self.why_btn.rect.collidepoint(mp) and self.design.complete() and self.problems()[0]:
            ui.draw_tooltip(s, self.why_btn.tooltip, mp)

    def draw_options(self, s):
        ui.panel(s, (2, 34, 250, 172), fill=NAVY, border=GREY)
        last_key = None
        for r, key, choice, c, (title, _) in self.cards:
            if key != last_key:
                ui.text(s, SECTION_TITLES[key], (8, r.y - 10), CYAN, 14)
                last_key = key
            ok, why = self.availability(key, choice)
            sel = self.design[key] == choice
            mp = pygame.mouse.get_pos()
            hov = r.collidepoint(mp)
            fill = (46, 80, 50) if sel else ((40, 40, 84) if hov else (24, 26, 56))
            if not ok and not sel:
                fill = (30, 22, 30)
            ui.panel(s, r, fill=fill, border=YELLOW if sel else (GREY if ok else (70, 50, 60)))
            col = WHITE if ok or sel else (110, 100, 110)
            ny = r.y + (0 if r.h < 22 else 2)
            ui.text(s, c["name"], (r.x + 4, ny), col, 14)
            cost = self.design.cost_with(key, choice) - self.design.cost_with(key, None)
            ctxt = ("$%dM" % round(cost)) if key != "material" else "x%.1f price" % c["cost"]
            ui.text(s, ctxt, (r.right - 4, ny), GOLD if ok else (110, 100, 110), 14, right=True)
            if r.h >= 17:
                compact = r.h < 22
                ui.text(s, option_summary(key, c), (r.x + 4, r.y + (10 if compact else 13)),
                        LIGHT if ok else (90, 90, 100), 12 if compact else 14, shadow=not compact)
            if not ok and not sel:
                ui.text(s, "X", (r.right - 58, ny), RED, 14)
        sid, title, keys = STEPS[self.step]
        if not any(self.availability(k, ch)[0] or self.design[k] == ch for _, k, ch, _, _ in self.cards):
            ui.panel(s, (258, 100, 214, 30), fill=DARKRED, border=RED)
            ui.text_block(s, "Nothing here fits your budget! Go back and pick cheaper parts.",
                          (262, 103, 208, 26), WHITE, 14)
        if self.flash > 0 and self.message:
            ui.panel(s, (258, 140, 214, 16), fill=DARKRED, border=RED)
            ui.text(s, self.message, (365, 143), WHITE, 14, center=True)

    def draw_pad(self, s):
        x0, y0, w, h = 254, 34, 222, 172
        ui.panel(s, (x0, y0, w, h), fill=(24, 30, 64), border=GREY)
        # sky gradient + ground
        for i in range(h - 4):
            c = (24 + i // 8, 30 + i // 6, 64 + i // 5)
            pygame.draw.line(s, c, (x0 + 2, y0 + 2 + i), (x0 + w - 3, y0 + 2 + i))
        ground = y0 + h - 18
        pygame.draw.rect(s, (60, 64, 60), (x0 + 2, ground, w - 4, 16))
        pygame.draw.rect(s, (90, 90, 96), (x0 + 60, ground - 4, 110, 4))  # pad
        for i in range(x0 + 4, x0 + w - 4, 6):
            s.set_at((i, ground + 6), (90, 96, 90))
        stack = art.draw_stack(self.design.c)
        sx = x0 + w // 2 - 32
        sy = ground - 4 - stack.get_height()
        ch = max(60, stack.get_height() + 6)
        cr = art.crane(ch)
        s.blit(cr, (x0 + w // 2 + 16, ground - 4 - ch))
        # crane arms holding the stack
        for yy in range(ground - 4 - ch + 10, ground - 10, 26):
            pygame.draw.rect(s, (210, 40, 40), (x0 + w // 2 + 6, yy, 12, 2))
        s.blit(stack, (sx, sy))
        if not self.design["lv_size"] and not self.design["ship"]:
            ui.text(s, "Empty launch pad", (x0 + w // 2, ground - 40), GREY, 14, center=True)
        ui.text(s, "LAUNCH COMPLEX 39", (x0 + 6, y0 + h - 14), LIGHT, 14)

    def draw_stats(self, s):
        st = self.partial_stats()
        a = st["analysis"]
        ui.panel(s, (2, 208, 476, 60), fill=(10, 12, 30), border=YELLOW)

        def fmt(v, f):
            return "--" if v is None else f % v

        cells = [
            ("MASS", fmt(st["mass"], "%.0f t")),
            ("COST", "$%dM" % self.design.total_cost()),
            ("HEAT RES", fmt(st["heat"], "%.0f")),
            ("STRENGTH", fmt(st["strength"], "%.0f")),
            ("THRUST", (fmt(st["thrust"], "%.0f kN") + (" TWR %.2f" % a["twr"] if a else ""))),
            ("MAX VEL", ("%.1f km/s" % a["max_vel"]) if a else "--"),
            ("ENERGY", fmt(st["energy"], "%+.1f/turn")),
            ("CARGO", ("%.1f/%d t" % (st["cargo_mass"], st["cargo_cap"])) if st["cargo_cap"] else "--"),
        ]
        for i, (lab, val) in enumerate(cells):
            cx = 8 + (i % 4) * 96
            cy = 212 + (i // 4) * 20
            ui.text(s, lab, (cx, cy), CYAN, 14)
            ui.text(s, val, (cx, cy + 9), WHITE, 14)
        if a:
            ui.text(s, "dV %.1f+%.1f / need %.1f km/s" % (a["lv_dv"] / 1000, a["ship_dv"] / 1000,
                                                       (a["orbit_need"] + a["transfer"]) / 1000),
                    (8, 252), LIGHT, 14)
            warns = self.warnings(a)
            if warns:
                c = RED if int(self.t * 3) % 2 == 0 else ORANGE
                msg = "! " + warns[0][1]
                if len(warns) > 1:
                    msg = "! %d problems: " % len(warns) + warns[0][1]
                while ui.font(14).size(msg)[0] > 186 and len(msg) > 4:
                    msg = msg[:-4] + "..."
                ui.text(s, msg, (146, 252), c, 14)
                self.why_btn.draw(s)
                if self.tutorial and not self.warned_complete and not self.mc.active:
                    self.warned_complete = True
                    self.mc.tip("build_why", [
                        "Mission Control has spotted a problem with this design!",
                        "Click the orange WHY? button. It explains what causes the problem and which parts affect it.",
                        "It won't tell you what to pick - you're the engineer! Change parts and watch the numbers."],
                                force=True)
            else:
                ui.text(s, "No problems detected", (146, 252), GREEN, 14)
            self.launch_btn.draw(s)
        else:
            missing = [STEPS[i][1] for i in range(len(STEPS)) if not all(self.design[k] for k in STEPS[i][2])]
            ui.text(s, "Still needed: " + ", ".join(m.title() for m in missing)[:70], (8, 252), ORANGE, 14)
