"""DESIGN MISSION: plan your own multi-stop mission (unlocked after completing Saturn).

* Start from any solid body you have unlocked: Earth, the Moon, Mars or Bennu.
* Visit 1-5 destinations you have unlocked (the Black Hole after its first visit).
* Choose a budget (a recommended budget is calculated for you).
* The Interplanetary Station (design missions only) carries one payload per stop.
  Any other ship carries one payload, deployed at the first stop that can use it;
  the other stops are science fly-bys.
* Fly leg by leg: choose a route before each leg. Fuel, food, energy, hull and crew
  health carry over between stops. Leaving Jupiter or Saturn gives a gravity assist.

Travel between any two places uses real Hohmann-transfer maths between the orbits
(sizes in AU), calibrated so trips from Earth match the main game's levels.
"""
import copy
import itertools
import math
import threading

import pygame

import art
import physics
import ui
from levels import LEVELS, LEVEL_BY_ID, ORDER
from scene import Scene, MissionControl
from settings import *
from spacecraft import (LV_SIZES, MATERIALS, SHIPS, SHIELDS, BOOSTERS, ENGINES, ENERGY, CARGO, DESIGN_KEYS,
                        Design, set_multi_cargo)

MAX_STOPS = 5
UNLOCK_AFTER = "saturn"
STARTS = ["earth", "moon", "mars", "asteroid"]        # solid bodies you can launch from
START_ICON = {"earth": "earth", "moon": "moon", "mars": "mars", "asteroid": "bennu"}
START_NAME = {"earth": "Earth", "moon": "The Moon", "mars": "Mars", "asteroid": "Bennu"}
ORBIT_AU = {"earth": 1.0, "moon": 1.0, "mars": 1.524, "venus": 0.723, "jupiter": 5.203, "saturn": 9.537,
            "sun": 0.05, "asteroid": 1.126, "blackhole": 9.537}
ASSIST = {"jupiter": 0.65, "saturn": 0.8}             # delta-v multiplier for the leg after leaving them
EARTH_V = 29.78                                       # km/s, Earth's orbital speed


# ------------------------------------------------------------------ travel maths
def hohmann_dv(r1, r2):
    """km/s for a two-burn Hohmann transfer between circular orbits r1, r2 (AU) around the Sun."""
    v1, v2 = EARTH_V / math.sqrt(r1), EARTH_V / math.sqrt(r2)
    a = (r1 + r2) / 2
    return abs(math.sqrt(r2 / a) - 1) * v1 + abs(1 - math.sqrt(r1 / a)) * v2


def hohmann_days(r1, r2):
    return 0.5 * ((r1 + r2) / 2) ** 1.5 * 365.25


def _cal(b):
    """Calibration factors so Earth -> b matches the main game's level values."""
    g = LEVEL_BY_ID[b]["game"]
    return g["transfer_dv"] / (hohmann_dv(1.0, ORBIT_AU[b]) * 1000), g["days"] / hohmann_days(1.0, ORBIT_AU[b])


def turns_for(days):
    return int(max(4, min(12, round(2 + 1.5 * math.log2(max(days, 1.0) / 8.0)))))


def leg_numbers(a, b):
    """(delta-v m/s, days, turns, note) to travel from a to b. a may be 'earth'."""
    if a == "earth" or (a == "moon" and b == "moon"):
        g = LEVEL_BY_ID[b]["game"]
        return g["transfer_dv"], g["days"], g["turns"], ""
    if b == "blackhole":
        if a == "saturn":
            return 2500.0, 150.0, 6, "wormhole next to Saturn"
        dv, days, _, _ = leg_numbers(a, "saturn")
        return dv + 2500.0, days + 150.0, turns_for(days + 150), "via the wormhole near Saturn"
    if a == "blackhole":
        if b == "saturn":
            return 2500.0, 150.0, 6, "back through the wormhole"
        dv, days, _, _ = leg_numbers("saturn", b)
        return dv + 2500.0, days + 150.0, turns_for(days + 150), "back through the wormhole"
    if a == "moon":                     # leaving lunar orbit is cheaper than leaving low Earth orbit
        g = LEVEL_BY_ID[b]["game"]
        return g["transfer_dv"] * 0.8, g["days"], g["turns"], "starting high in Earth's gravity well"
    if b == "moon":
        dv, days, _, _ = leg_numbers("earth", a)
        return dv * 0.9 + 900.0, days, turns_for(days), "back to Earth's neighbourhood"
    if "asteroid" in (a, b):            # Bennu is a near-Earth asteroid: like an Earth trip plus a rendezvous
        other = b if a == "asteroid" else a
        g = LEVEL_BY_ID[other]["game"]
        dv, days = g["transfer_dv"] * 0.9 + 2600.0, g["days"] + 150.0
        note = ""
        if a in ASSIST:
            dv *= ASSIST[a]
            days *= 0.6
            note = "gravity assist from %s" % LEVEL_BY_ID[a]["name"]
        return dv, days, turns_for(days), note
    ra, rb = ORBIT_AU[a], ORBIT_AU[b]
    fa, da = _cal(a)
    fb, db = _cal(b)
    if b == "sun":
        f, df = fb, db
    elif a == "sun":
        f, df = fa, da
    else:
        f, df = (fa + fb) / 2, (da + db) / 2
    dv = max(1500.0, hohmann_dv(ra, rb) * 1000 * f)
    days = max(5.0, hohmann_days(ra, rb) * df)
    note = ""
    if a in ASSIST:
        dv *= ASSIST[a]
        days *= 0.6
        note = "gravity assist from %s: -%d%% delta-v, faster trip" % (LEVEL_BY_ID[a]["name"],
                                                                      round((1 - ASSIST[a]) * 100))
    return dv, days, turns_for(days), note


def preferred_cargo(stop):
    return LEVEL_BY_ID[stop]["game"]["allowed_cargo"][0]


def make_leg(a, b, index, total, launch=None):
    lv = copy.deepcopy(LEVEL_BY_ID[b])
    g = lv["game"]
    dv, days, turns, note = leg_numbers(a, b)
    g["transfer_dv"], g["days"], g["turns"] = dv, days, turns
    g["au_start"], g["au_end"] = ORBIT_AU[a], ORBIT_AU[b]
    if launch:
        g["launch"] = launch
    lv.pop("tutorial", None)
    lv.pop("final", None)
    lv["design_leg"] = True
    lv["from"] = a
    lv["from_name"] = START_NAME.get(a) or LEVEL_BY_ID[a]["name"]
    lv["from_icon"] = START_ICON.get(a) or LEVEL_BY_ID[a]["icon"]
    lv["leg"] = (index + 1, total)
    lv["assist_note"] = note
    lv["objective"] = "Leg %d of %d: %s to %s." % (index + 1, total, lv["from_name"], lv["name"])
    return lv


def virtual_level(start, stops, budget):
    """One combined 'level' used by the build screen to check the whole trip."""
    legs = [make_leg(([start] + stops)[i], stops[i], i, len(stops), start if i == 0 else None)
            for i in range(len(stops))]
    allowed = []
    for s_ in stops:
        for c in LEVEL_BY_ID[s_]["game"]["allowed_cargo"]:
            if c not in allowed:
                allowed.append(c)
    if len(stops) > 1:
        allowed.append("multi")
    rs = [ORBIT_AU[x] for x in stops]
    far = max(rs) if max(rs) > 1.6 else min(rs)
    bias = {}
    for s_ in stops:
        for k, v in LEVEL_BY_ID[s_]["game"]["event_bias"].items():
            bias[k] = max(bias.get(k, 1.0), v)
    need = int(round(sum(LEVEL_BY_ID[s_]["game"]["science_needed"] for s_ in stops) * 0.5 / 10.0) * 10)
    names = " > ".join(LEVEL_BY_ID[s_]["name"].replace("Asteroid ", "") for s_ in stops)
    return dict(
        id="design", name="Design Mission", icon=LEVEL_BY_ID[stops[0]]["icon"], design=True,
        real={}, objective="Your mission: %s to %s." % (START_NAME[start], names),
        game=dict(
            budget=budget, transfer_dv=legs[0]["game"]["transfer_dv"],
            extra_dv=sum(l["game"]["transfer_dv"] for l in legs[1:]),
            days=sum(l["game"]["days"] for l in legs), turns=sum(l["game"]["turns"] for l in legs),
            au_start=ORBIT_AU[start], au_end=far, allowed_cargo=allowed,
            entry_heat=max(LEVEL_BY_ID[s_]["game"]["entry_heat"] for s_ in stops), landing_g=1.0,
            science_needed=need, science_mult=sum(LEVEL_BY_ID[s_]["game"]["science_mult"] for s_ in stops) / len(stops),
            event_chance=sum(LEVEL_BY_ID[s_]["game"]["event_chance"] for s_ in stops) / len(stops),
            event_bias=bias, launch=start, dv_note="Your own multi-stop mission",
        ),
    ), legs


# ------------------------------------------------------------------ recommended budget
_COST_SORTED = None


def _all_designs():
    """Every design, cheapest first (cost does not depend on the mission)."""
    global _COST_SORTED
    if _COST_SORTED is None:
        out = []
        for combo in itertools.product(LV_SIZES, MATERIALS, SHIPS, SHIELDS, BOOSTERS, ENGINES, ENERGY,
                                       [c for c in CARGO if c != "multi"] + ["multi"]):
            d = Design(dict(zip(DESIGN_KEYS, combo)))
            out.append(d)
        _COST_SORTED = out
    return _COST_SORTED


def cheapest_design(vlevel, stops, cancel=lambda: False):
    """Cheapest design that passes every check for the whole trip (all objectives if several stops)."""
    multi = len(stops) > 1
    cands = []
    for d in _all_designs():
        if multi and (d["ship"] != "station" or d["cargo"] != "multi"):
            continue
        if not multi and (d["ship"] == "station" or d["cargo"] == "multi"):
            continue
        if d["cargo"] == "multi" and "multi" not in CARGO:
            continue
        cands.append((d.total_cost(), d))
    cands.sort(key=lambda x: x[0])
    for i, (cost, d) in enumerate(cands):
        if i % 200 == 0 and cancel():
            return None
        a = physics.analyze(d.c, vlevel)
        if not a["cargo_allowed"] or not a["cargo_fits"]:
            continue
        if not physics.predicted_failures(a) and a["margin"] > 300:
            return cost, d
    return None


# ------------------------------------------------------------------ mission state
class DesignMission:
    def __init__(self, start, stops, budget):
        self.start, self.stops, self.budget = start, list(stops), budget
        set_multi_cargo([preferred_cargo(s_) for s_ in stops])
        self.vlevel, self.legs = virtual_level(start, stops, budget)
        self.index = 0
        self.results = []
        self.plan = [None] * len(stops)
        self.design = None

    def begin(self, design):
        """Called when the player launches: reset progress and work out which stop gets which payload."""
        self.design = design.copy()
        self.index = 0
        self.results = []
        cargo = design["cargo"]
        if cargo == "multi":
            self.plan = [preferred_cargo(s_) for s_ in self.stops]
        else:
            self.plan = [None] * len(self.stops)
            for i, s_ in enumerate(self.stops):
                if cargo in LEVEL_BY_ID[s_]["game"]["allowed_cargo"]:
                    self.plan[i] = cargo
                    break

    def leg(self, i=None):
        return self.legs[self.index if i is None else i]

    def record(self, ms, flyby_science=0.0):
        self.results.append(dict(stop=self.stops[self.index], cargo=self.plan[self.index],
                                 done=bool(ms.objective_done), quality=ms.objective_quality,
                                 science=ms.science, flyby=flyby_science))

    def after_stop(self, game, ms):
        """A stop is finished (objective or fly-by). Continue to the next leg or the final report."""
        self.index += 1
        if self.index < len(self.stops):
            game.switch(LegComplete(game), loading=True, label="NEXT LEG")
        else:
            game.switch(DesignReport(game), loading=True, label="MISSION COMPLETE")


def is_unlocked(save):
    return UNLOCK_AFTER in save.data["completed"]


def available_starts(save):
    return [s_ for s_ in STARTS if s_ == "earth" or s_ in save.data["unlocked"] or s_ in save.data["completed"]]


def available_stops(save):
    out = []
    for lid in ORDER:
        if lid == "blackhole":
            if "blackhole" in save.data["completed"]:
                out.append(lid)
        elif lid in save.data["unlocked"] or lid in save.data["completed"]:
            out.append(lid)
    return out


# ------------------------------------------------------------------ planner screen
class DesignPlanner(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        sd = game.save
        self.starts = available_starts(sd)
        self.stops_ok = available_stops(sd)
        prev = game.save.data.get("design_last") or {}
        self.start = prev.get("start", "earth") if prev.get("start") in self.starts else "earth"
        self.stops = [x for x in prev.get("stops", []) if x in self.stops_ok][:MAX_STOPS]
        self.budget = int(prev.get("budget", 2500))
        self.recommended = None       # (cost, design) / "none" / None while calculating
        self.calc_token = 0
        self.message = ""
        self.mc = MissionControl(game, (4, 196, 472, 70))
        self.mc.tip("design_intro", [
            "Welcome to DESIGN MISSION, {name}! Here YOU plan the mission.",
            "1. Pick where to launch from.  2. Click up to 5 destinations in the order you want to visit them.",
            "3. Set your budget - I'll calculate a recommended budget for the cheapest ship that can do it all.",
            "With several stops you'll want the new INTERPLANETARY STATION: it carries one payload for every stop.",
        ])
        self.make_buttons()
        self.recalc()

    # ---------------------------------------------------------- buttons
    def make_buttons(self):
        b = []
        for i, s_ in enumerate(STARTS):
            ok = s_ in self.starts
            b.append(ui.Button((8, 46 + i * 24, 92, 20), START_NAME[s_], lambda s_=s_: self.set_start(s_),
                               color=DARKGREEN if s_ == self.start else DARK, size=14, enabled=ok,
                               tooltip=None if ok else "Unlock this level first"))
        for i, lid in enumerate(ORDER):
            lv = LEVEL_BY_ID[lid]
            ok = lid in self.stops_ok
            tip = None if ok else ("Complete the Black Hole finale first" if lid == "blackhole"
                                   else "Unlock this level first")
            b.append(ui.Button((112 + (i % 4) * 66, 46 + (i // 4) * 24, 62, 20),
                               lv["name"].replace("Asteroid ", "").replace("The ", ""),
                               lambda lid=lid: self.add_stop(lid), color=BLUE, size=14, enabled=ok, tooltip=tip))
        b.append(ui.Button((114, 145, 54, 15), "UNDO", self.undo, color=DARK, size=14, sound="back"))
        b.append(ui.Button((172, 145, 54, 15), "CLEAR", self.clear, color=DARK, size=14, sound="back"))
        b.append(ui.Button((392, 66, 26, 18), "-", lambda: self.change_budget(-100), color=DARK, size=18))
        b.append(ui.Button((448, 66, 26, 18), "+", lambda: self.change_budget(100), color=DARK, size=18))
        b.append(ui.Button((384, 112, 92, 16), "USE RECOMMENDED", self.use_recommended, color=PURPLE, size=14))
        b.append(ui.Button((4, 172, 80, 20), "< MAP", self.back, color=DARK, text_color=YELLOW, size=14,
                           sound="back"))
        b.append(ui.Button((330, 170, 146, 24), "TO THE LAUNCH PAD", self.go, color=RED, size=16, sound="select",
                           enabled=bool(self.stops)))
        self.buttons = b

    def set_start(self, s_):
        self.start = s_
        if self.stops and self.stops[0] == s_:
            self.stops.pop(0)
        self.changed()

    def add_stop(self, lid):
        prev = self.stops[-1] if self.stops else self.start
        if len(self.stops) >= MAX_STOPS:
            self.message = "Maximum of %d destinations." % MAX_STOPS
            self.audio.play("deny")
            return
        if lid == prev:
            self.message = "You are already there! Pick a different next stop."
            self.audio.play("deny")
            return
        self.stops.append(lid)
        self.changed()

    def undo(self):
        if self.stops:
            self.stops.pop()
            self.changed()

    def clear(self):
        self.stops = []
        self.changed()

    def change_budget(self, d):
        self.budget = max(500, min(20000, self.budget + d))

    def use_recommended(self):
        if isinstance(self.recommended, tuple):
            self.budget = self.rec_budget()

    def rec_budget(self):
        return int(math.ceil(self.recommended[0] * 1.15 / 50.0) * 50)

    def changed(self):
        self.message = ""
        self.make_buttons()
        self.recalc()

    def recalc(self):
        """Work out the recommended budget in the background (it checks thousands of designs)."""
        self.calc_token += 1
        token = self.calc_token
        self.recommended = None
        if not self.stops:
            return
        start, stops = self.start, list(self.stops)

        def work():
            set_multi_cargo([preferred_cargo(s_) for s_ in stops])
            vl, _ = virtual_level(start, stops, 99999)
            res = cheapest_design(vl, stops, cancel=lambda: token != self.calc_token)
            if token == self.calc_token:
                self.recommended = res if res else "none"

        import sys
        if sys.platform == "emscripten":   # web build: no threads, just calculate now (it is quick)
            work()
            return
        try:
            threading.Thread(target=work, daemon=True).start()
        except RuntimeError:
            work()

    def back(self):
        from levelselect import LevelSelect
        self.calc_token += 1
        self.game.switch(LevelSelect(self.game))

    def go(self):
        if not self.stops:
            return
        self.calc_token += 1
        self.game.save.data["design_last"] = dict(start=self.start, stops=self.stops, budget=self.budget)
        self.game.save.save()
        dm = DesignMission(self.start, self.stops, self.budget)
        self.game.design_mission = dm
        from build import BuildScene
        self.game.switch(BuildScene(self.game, dm.vlevel), loading=True, label="TO THE LAUNCH PAD")

    # ---------------------------------------------------------- loop
    def handle(self, e):
        if self.mc.handle(e):
            return True
        if self.mc.active:
            return True
        return super().handle(e)

    def update(self, dt):
        self.t += dt
        self.mc.update(dt)
        self.game.stars.update(dt, 8)

    def draw(self, s):
        self.game.stars.draw(s, 0.7)
        ui.panel(s, (0, 0, W, 18), fill=(10, 10, 28), border=YELLOW)
        ui.text(s, "DESIGN YOUR OWN MISSION", (W // 2, 3), YELLOW, 16, center=True)
        ui.text(s, "1. LAUNCH FROM", (8, 26), CYAN, 14)
        ui.text(s, "solid ground only", (8, 36), GREY, 12)
        ui.text(s, "2. DESTINATIONS IN ORDER (max %d)" % MAX_STOPS, (112, 26), CYAN, 14)
        ui.text(s, "3. BUDGET", (384, 26), CYAN, 14)
        # budget
        ui.text(s, "$%dM" % self.budget, (433, 44), WHITE, 20, center=True)
        rec = self.recommended
        if not self.stops:
            txt, col = "Add a destination", GREY
        elif rec is None:
            txt, col = "Calculating" + "." * (int(self.t * 3) % 4), LIGHT
        elif rec == "none":
            txt, col = "No ship can do this - try fewer or closer stops", RED
        else:
            txt, col = "Recommended: $%dM" % self.rec_budget(), GREEN
        if rec == "none":
            ui.text_block(s, txt, (384, 86, 92, 26), col, 12)
        elif isinstance(rec, tuple):
            ui.text(s, "Recommended", (430, 88), col, 12, center=True)
            ui.text(s, "$%dM" % self.rec_budget(), (430, 97), col, 14, center=True)
        else:
            ui.text(s, txt, (430, 92), col, 14, center=True)
        if isinstance(rec, tuple):
            ok = self.budget >= rec[0]
            ui.text(s, "enough" if ok else "too low!", (430, 130), GREEN if ok else ORANGE, 12, center=True)
        # route strip
        ui.panel(s, (108, 100, 268, 64), fill=(14, 16, 44), border=GREY)
        nodes = [("start", self.start)] + [("stop", x) for x in self.stops]
        x0 = 120
        for i, (kind, lid) in enumerate(nodes):
            icon = START_ICON[lid] if kind == "start" else LEVEL_BY_ID[lid]["icon"]
            p = art.planet(icon, 8)
            cx = x0 + i * 43
            s.blit(p, (cx - p.get_width() // 2 + 8, 113 - p.get_height() // 2))
            name = (START_NAME[lid] if kind == "start" else LEVEL_BY_ID[lid]["name"]).replace("Asteroid ", "")
            ui.text(s, name.replace("The ", "")[:7], (cx + 8, 123), WHITE if kind == "stop" else CYAN, 12,
                    center=True)
            if i:
                pygame.draw.line(s, RED, (cx - 26, 113), (cx - 8, 113), 1)
        if not self.stops:
            ui.text(s, "Click destinations above", (242, 108), GREY, 14, center=True)
        else:
            vl, legs = virtual_level(self.start, self.stops, self.budget)
            g = vl["game"]
            ui.text(s, "%d days, %d turns, dV %.1f km/s, science %d" % (
                g["days"], g["turns"], (g["transfer_dv"] + g["extra_dv"]) / 1000, g["science_needed"]),
                    (242, 134), LIGHT, 12, center=True)
        if self.message:
            ui.text(s, self.message, (240, 176), ORANGE, 14, center=True)
        elif len(self.stops) > 1:
            ui.text(s, "Several stops: use the INTERPLANETARY STATION", (205, 178), YELLOW, 12, center=True)
        self.draw_buttons(s, 1 / 60)
        self.mc.draw(s)


# ------------------------------------------------------------------ between legs
class LegComplete(Scene):
    music = "mission"

    def __init__(self, game):
        super().__init__(game)
        self.dm = game.design_mission
        self.ms = game.mission
        self.t = 0.0
        last = self.dm.results[-1]
        self.last = last
        self.buttons = [ui.Button((170, 236, 140, 24), "PLAN NEXT LEG >", self.next_leg, color=DARKGREEN, size=16,
                                  sound="select", key=pygame.K_RETURN)]

    def next_leg(self):
        from trajectory import TrajectoryScene
        self.game.switch(TrajectoryScene(self.game, self.dm.leg(), self.ms.design))

    def update(self, dt):
        self.t += dt
        self.game.stars.update(dt, 10)

    def draw(self, s):
        self.game.stars.draw(s)
        dm, ms = self.dm, self.ms
        ui.text(s, "STOP %d OF %d COMPLETE" % (dm.index, len(dm.stops)), (W // 2, 10), GREEN, 24, center=True)
        stop = LEVEL_BY_ID[self.last["stop"]]
        p = art.planet(stop["icon"], 20)
        s.blit(p, (60 - p.get_width() // 2, 80 - p.get_height() // 2))
        ui.panel(s, (110, 46, 340, 110), fill=NAVY, border=GREEN)
        what = ("Objective complete with the %s!" % CARGO[self.last["cargo"]]["name"].lower()
                if self.last["done"] else
                ("Science fly-by (+%d science)" % self.last["flyby"] if self.last["flyby"] else "Objective failed"))
        ui.text(s, stop["name"].upper(), (120, 52), YELLOW, 16)
        ui.text(s, what, (120, 70), WHITE, 14)
        rows = [("Science so far", "%d / %d" % (ms.science, dm.vlevel["game"]["science_needed"])),
                ("Energy / Food / Fuel", "%d%% / %d%% / %d%%" % (ms.pct("energy"), ms.pct("food"), ms.pct("fuel"))),
                ("Hull / Crew", "%d%% / %d%%" % (ms.integrity, ms.crew)),
                ("Next", "%s to %s" % (stop["name"], dm.leg()["name"]))]
        for i, (k, v) in enumerate(rows):
            ui.text(s, k, (120, 90 + i * 14), LIGHT, 14)
            ui.text(s, v, (440, 90 + i * 14), WHITE, 14, right=True)
        note = dm.leg()["assist_note"]
        if note:
            ui.text(s, "BONUS: " + note, (W // 2, 168), GREEN, 14, center=True)
        ui.text(s, "Supplies carry over - plan the next route carefully.", (W // 2, 186), LIGHT, 14, center=True)
        self.draw_buttons(s, 1 / 60)


class DesignReport(Scene):
    music = "menu"

    def __init__(self, game):
        super().__init__(game)
        self.dm = game.design_mission
        self.ms = game.mission
        self.t = 0.0
        need = self.dm.vlevel["game"]["science_needed"]
        self.done = sum(1 for r in self.dm.results if r["done"])
        self.alive = self.ms.failed is None
        self.passed = self.alive and self.ms.science >= need and self.done >= 1
        self.score = int(self.ms.science * 10 + self.done * 800 + (1000 if self.alive else 0)
                         + self.ms.crew * 3 + self.ms.integrity * 3
                         + max(0, self.dm.budget - self.dm.design.total_cost()))
        sd = game.save.data
        key = "design:" + ">".join([self.dm.start] + self.dm.stops)
        sd["best_scores"][key] = max(sd["best_scores"].get(key, 0), self.score)
        game.save.save()
        self.buttons = [
            ui.Button((90, 244, 140, 20), "DESTINATION MAP", self.levels, color=GREEN, text_color=BLACK, size=16),
            ui.Button((250, 244, 140, 20), "PLAN ANOTHER", self.again, color=DARK, text_color=YELLOW, size=16),
        ]

    def levels(self):
        from levelselect import LevelSelect
        self.game.design_mission = None
        self.game.switch(LevelSelect(self.game), loading=True)

    def again(self):
        self.game.design_mission = None
        self.game.switch(DesignPlanner(self.game))

    def update(self, dt):
        self.t += dt
        self.game.stars.update(dt, 8)

    def draw(self, s):
        self.game.stars.draw(s)
        dm, ms = self.dm, self.ms
        ui.text(s, "DESIGN MISSION SUCCESS!" if self.passed else "DESIGN MISSION INCOMPLETE", (W // 2, 8),
                GREEN if self.passed else ORANGE, 24, center=True)
        ui.panel(s, (30, 36, 420, 200), fill=NAVY, border=GREEN if self.passed else ORANGE)
        ui.text(s, "FROM %s" % START_NAME[dm.start].upper(), (40, 42), CYAN, 14)
        for i, r in enumerate(dm.results):
            lv = LEVEL_BY_ID[r["stop"]]
            y = 58 + i * 16
            p = art.planet(lv["icon"], 5)
            s.blit(p, (44, y - 1))
            ui.text(s, lv["name"], (62, y), WHITE, 14)
            if r["done"]:
                txt, col = "%s - objective complete (%d%%)" % (CARGO[r["cargo"]]["name"], r["quality"] * 100), GREEN
            elif r["flyby"]:
                txt, col = "science fly-by +%d" % r["flyby"], CYAN
            else:
                txt, col = "objective failed", RED
            ui.text(s, txt, (180, y), col, 14)
        y = 58 + max(1, len(dm.results)) * 16 + 8
        rows = [("Stops reached", "%d / %d" % (len(dm.results), len(dm.stops))),
                ("Objectives complete", "%d" % self.done),
                ("Science", "%d / %d needed" % (ms.science, dm.vlevel["game"]["science_needed"])),
                ("Crew health / hull", "%d%% / %d%%" % (ms.crew, ms.integrity)),
                ("Budget used", "$%dM of $%dM" % (dm.design.total_cost(), dm.budget))]
        for i, (k, v) in enumerate(rows):
            ui.text(s, k, (40, y + i * 13), LIGHT, 14)
            ui.text(s, v, (440, y + i * 13), WHITE, 14, right=True)
        ui.text(s, "SCORE  %d" % self.score, (W // 2, 220), YELLOW, 20, center=True)
        self.draw_buttons(s, 1 / 60)
