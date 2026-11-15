"""Mission state (resources, turns, burns) and the main mission interface."""
import math
import random

import pygame

import art
import physics
import routes
import science
import systems
import ui
from scene import Scene, MissionControl, FactPopup
from settings import *
from spacecraft import SHIPS, SHIELDS, ENGINES, ENERGY, CARGO

LOAD_MULT = 1.1          # in-flight power use vs the build-screen estimate (heaters, comms...)
PRECISE_FUEL = 0.8       # a PRECISE burn uses 20% less propellant...
PRECISE_ENERGY = 8       # ...but costs this much energy (% of battery) per major burn
MAJOR_BURN = 300         # m/s; smaller course corrections don't cost extra energy


def make_burn_plan(a, engine, n):
    """Delta-v (m/s) the spacecraft burns at the end of each of its n turns."""
    T = a["transfer"]
    st = a["ship_transfer"]
    plan = [0.0] * n
    if engine == "ion":
        for i in range(n):
            plan[i] = st / n
    elif engine != "sail":
        departure = max(0.0, st - 0.30 * T)
        mid = 0.05 * T
        arrive = 0.25 * T
        plan[0] += departure
        if n > 2:
            for i in range(1, n - 1):
                plan[i] += mid / (n - 2)
        else:
            arrive += mid
        plan[-1] += arrive
    return plan


def fuel_for_plan(isp, dry, burns, precise=False):
    """Minimum propellant (t) to perform the burns in order (worked out backwards)."""
    if isp <= 0:
        return 0.0
    ve = isp * physics.G0
    m = dry
    for dv in reversed(burns):
        f = m * (math.exp(dv / ve) - 1.0)
        if precise:
            f *= PRECISE_FUEL
        m += f
    return m - dry


def route_preview(design, level, route_id):
    """Numbers for the trajectory screen: what this design needs on this route."""
    lv = routes.apply_route(level, route_id)
    a = physics.analyze(design.c, lv)
    eng = ENGINES[design["engine"]]
    out = dict(level=lv, a=a, days=a["days"], turns=lv["game"]["turns"], food=a["food_days"],
               sail=design["engine"] == "sail", dv_need=a["ship_needed"], dv_have=a["ship_dv"])
    fuel = a["ship_fuel"]
    if eng["isp"] > 0 and fuel > 0:
        left = fuel - physics.fuel_for_dv(eng["isp"], a["ship_dry"] + fuel, a["orbit_deficit"])
        plan = make_burn_plan(a, design["engine"], lv["game"]["turns"])
        out["fuel_std"] = 100.0 * fuel_for_plan(eng["isp"], a["ship_dry"], plan) / fuel
        out["fuel_precise"] = 100.0 * fuel_for_plan(eng["isp"], a["ship_dry"], plan, True) / fuel
        out["fuel_after_orbit"] = 100.0 * max(0.0, left) / fuel
    else:
        out["fuel_std"] = out["fuel_precise"] = 0.0
        out["fuel_after_orbit"] = 100.0
    # power forecast: battery left at the end (% of storage), allowing for system alerts
    en, g = ENERGY[design["energy"]], lv["game"]
    load = a["energy_load"] * LOAD_MULT * routes.ROUTES[route_id]["power"]
    n = g["turns"]
    gen = sum(physics.generation(en, g, t, n) for t in range(n))
    alerts = n * systems.ALERT_CHANCE * 0.09 * en["storage"]
    if design["engine"] != "sail" and out["fuel_std"] > out["fuel_after_orbit"]:   # will need precise burns
        plan = make_burn_plan(a, design["engine"], n)
        alerts += sum(1 for b in plan if b >= MAJOR_BURN) * PRECISE_ENERGY / 100.0 * en["storage"]
    out["power_end"] = 100.0 * (en["storage"] + gen - n * load - alerts) / en["storage"]
    out["power_end_eco"] = 100.0 * (en["storage"] + gen - n * load * 0.6 - alerts) / en["storage"]
    return out


def route_preview_continue(ms, leg_level, route_id):
    """Trajectory-screen numbers for the next leg of a Design Mission, from the ship's CURRENT supplies."""
    lv = routes.apply_route(leg_level, route_id)
    a = dict(physics.analyze(ms.design.c, lv))
    a["orbit_deficit"] = 0.0
    a["ship_transfer"] = a["transfer"]
    days = physics.travel_days(ms.design.c, lv)
    out = dict(level=lv, a=a, days=days, turns=lv["game"]["turns"], food=ms.food,
               sail=ms.design["engine"] == "sail", dv_need=a["transfer"], dv_have=physics.sail_dv(lv))
    if ms.eng["isp"] > 0 and ms.fuel_cap > 0.001:
        plan = make_burn_plan(a, ms.design["engine"], lv["game"]["turns"])
        out["fuel_std"] = 100.0 * fuel_for_plan(ms.eng["isp"], a["ship_dry"], plan) / ms.fuel_cap
        out["fuel_precise"] = 100.0 * fuel_for_plan(ms.eng["isp"], a["ship_dry"], plan, True) / ms.fuel_cap
        out["fuel_after_orbit"] = ms.pct("fuel")
    else:
        out["fuel_std"] = out["fuel_precise"] = 0.0
        out["fuel_after_orbit"] = 100.0
    n = lv["game"]["turns"]
    load = a["energy_load"] * LOAD_MULT * routes.ROUTES[route_id]["power"]
    gen = sum(physics.generation(ms.en, lv["game"], t, n) for t in range(n)) * ms.solar_degrade
    alerts = n * systems.ALERT_CHANCE * 0.09 * ms.energy_cap
    out["power_end"] = 100.0 * (ms.energy + gen - n * load - alerts) / ms.energy_cap
    out["power_end_eco"] = 100.0 * (ms.energy + gen - n * load * 0.6 - alerts) / ms.energy_cap
    return out


class MissionState:
    """All numbers of a running mission. Kept separate from drawing code."""

    def __init__(self, game, level, design, route="direct"):
        self.game = game
        self.base_level = level            # unmodified level (used for retries)
        self.route = route
        self.route_info = routes.ROUTES[route]
        level = routes.apply_route(level, route)
        self.level = level
        self.design = design.copy()
        self.a = physics.analyze(self.design.c, level)
        g = level["game"]
        d = self.design
        self.ship = SHIPS[d["ship"]]
        self.eng = ENGINES[d["engine"]]
        self.en = dict(ENERGY[d["energy"]])   # copy: fuel cell life can change in flight
        self.cargo = CARGO[d["cargo"]]          # what the ship carries (mass, power use)
        self.dm = game.design_mission if level.get("design_leg") else None
        self.deploy_key = self.dm.plan[self.dm.index] if self.dm else d["cargo"]   # payload used at this stop
        self.turns_total = g["turns"]
        self.base_turns = g["turns"]
        self.days_total = self.a["days"]
        self.days_per_turn = self.days_total / self.turns_total
        self.turn = 0
        self.day = 0.0
        self.energy_cap = self.en["storage"]
        self.energy = self.energy_cap
        self.food_cap = self.ship["food_days"]
        self.food = self.food_cap
        self.fuel_cap = max(0.001, self.a["ship_fuel"])
        self.fuel = self.a["ship_fuel"]
        self.shield_cap = SHIELDS[d["shield"]]["durability"]
        self.shield = self.shield_cap
        self.integrity = 100.0
        self.crew = 100.0         # crew health: radiation and injuries. 0 = mission failed
        self.life = None          # life support % once energy hits zero
        self.science = 0.0
        self.exp_counts = {}
        self.experiments_run = 0
        self.did_experiment = False
        self.power_mode = "normal"
        self.rations = False
        self.spares = self.ship["spares"]
        self.gen_offline = 0
        self.solar_degrade = 1.0
        self.encounter = None     # 'pirate' / 'astronaut' met this mission (enables experiment)
        self.event_counts = {}
        self.last_event = None
        self.failed = None
        self.objective_done = False
        self.objective_quality = 0.0
        self.log = []
        self.shortfall = 0.0
        self.burn_plan = []
        self.used_emergency = False
        self.used_repair = False
        self.burn_mode = "standard"   # or 'precise'
        self.turn_gen_mult = 1.0      # set by system alerts, reset every turn
        self.turn_sci_mult = 1.0
        self.last_alert = None
        self.used_questions = set()

    # ------------------------------------------------------------ helpers
    def pct(self, k):
        cap = {"energy": self.energy_cap, "food": self.food_cap, "fuel": self.fuel_cap,
               "shield": max(1, self.shield_cap), "integrity": 100.0, "crew": 100.0}[k]
        if k == "fuel" and self.design["engine"] == "sail":
            return 100.0
        return max(0.0, min(100.0, 100.0 * getattr(self, k) / cap))

    def progress(self):
        return min(1.0, self.turn / max(1, self.turns_total))

    def add_log(self, msg):
        self.log.append(msg)
        self.log = self.log[-4:]

    def fail(self, reason):
        if not self.failed:
            self.failed = reason

    def apply(self, changes):
        """changes: {'energy': -10, 'food': +5, ...} in percent of capacity, except
        integrity/shield which are absolute points."""
        for k, v in changes.items():
            if k == "energy":
                self.energy = max(0.0, min(self.energy_cap, self.energy + v / 100.0 * self.energy_cap))
            elif k == "food":
                self.food = max(0.0, min(self.food_cap, self.food + v / 100.0 * self.food_cap))
            elif k == "fuel":
                self.fuel = max(0.0, min(self.fuel_cap, self.fuel + v / 100.0 * self.fuel_cap))
            elif k == "shield":
                self.shield = max(0.0, min(self.shield_cap, self.shield + v))
            elif k == "integrity":
                dmg = v
                if v < 0:  # stronger ships take less damage
                    dmg = v * 60.0 / max(30.0, self.a["strength"])
                self.integrity = max(0.0, min(100.0, self.integrity + dmg))
            elif k == "crew":
                self.crew = max(0.0, min(100.0, self.crew + v))
            elif k == "science":
                self.science += v
        if self.crew <= 0:
            self.fail("The crew's health gave out - radiation sickness and injuries were too severe")
        if self.integrity <= 0:
            self.fail("Structural failure - the spacecraft broke apart")

    # ------------------------------------------------------------ launch
    def after_launch(self):
        """Apply ascent wear and plan the spacecraft's burns."""
        a = self.a
        self.shield = max(0.0, self.shield - 15.0 * physics.ASCENT_HEAT_NEED / max(1.0, a["heat"]))
        self.integrity -= 8.0 * 60.0 / a["strength"]
        if a["orbit_deficit"] > 0 and self.eng["isp"] > 0:
            used = physics.fuel_for_dv(self.eng["isp"], self.a["ship_dry"] + self.fuel, a["orbit_deficit"])
            self.fuel = max(0.0, self.fuel - used)
        self.burn_plan = make_burn_plan(a, self.design["engine"], self.turns_total)

    def start_leg(self, leg_level, route):
        """Design Mission: begin the next leg. Supplies, hull, crew and science carry over."""
        self.base_level = leg_level
        self.route = route
        self.route_info = routes.ROUTES[route]
        self.level = routes.apply_route(leg_level, route)
        a = dict(physics.analyze(self.design.c, self.level))
        a["orbit_deficit"] = 0.0
        a["ship_transfer"] = a["transfer"]
        a["margin"] = (physics.sail_dv(self.level) - a["transfer"]) if self.design["engine"] == "sail" else 1.0
        self.a = a
        g = self.level["game"]
        self.turns_total = self.base_turns = g["turns"]
        self.days_total = physics.travel_days(self.design.c, self.level)
        self.days_per_turn = self.days_total / self.turns_total
        self.turn = 0
        self.exp_counts = {}
        self.event_counts = {}
        self.last_event = None
        self.shortfall = 0.0
        self.objective_done = False
        self.objective_quality = 0.0
        self.deploy_key = self.dm.plan[self.dm.index]
        self.burn_plan = make_burn_plan(a, self.design["engine"], self.turns_total)

    def fuel_needed_pct(self, precise=None):
        """% of a full tank still needed for the burns from this turn on."""
        if self.design["engine"] == "sail" or self.eng["isp"] <= 0:
            return 0.0
        if precise is None:
            precise = self.burn_mode == "precise"
        rest = self.burn_plan[max(0, self.turn - 1):]
        return 100.0 * fuel_for_plan(self.eng["isp"], self.a["ship_dry"], rest, precise) / self.fuel_cap

    def burn_this_turn(self):
        i = self.turn - 1
        return self.burn_plan[i] if 0 <= i < len(self.burn_plan) else 0.0

    def burn(self, dv):
        """Burn engines for dv (m/s). Returns dv actually achieved."""
        if dv <= 0 or self.design["engine"] == "sail":
            return dv
        need = physics.fuel_for_dv(self.eng["isp"], self.a["ship_dry"] + self.fuel, dv)
        if self.burn_mode == "precise":
            need *= PRECISE_FUEL
        if need <= self.fuel:
            self.fuel -= need
            return dv
        # not enough propellant: burn what's left
        achieved = physics.rocket_dv(self.eng["isp"], self.a["ship_dry"] + self.fuel, self.a["ship_dry"])
        self.fuel = 0.0
        self.shortfall += dv - achieved
        return achieved

    # ------------------------------------------------------------ turns
    def begin_turn(self):
        self.turn += 1
        self.did_experiment = False
        self.used_emergency = False
        self.used_repair = False
        self.turn_gen_mult = 1.0
        self.turn_sci_mult = 1.0

    def end_turn(self):
        """Resource update at the end of a turn. Returns list of messages."""
        msgs = []
        g = self.level["game"]
        i = self.turn - 1
        if 0 <= i < len(self.burn_plan) and self.burn_plan[i] > 0 and self.design["engine"] != "sail":
            self.burn(self.burn_plan[i])
            if self.burn_mode == "precise" and self.burn_plan[i] >= MAJOR_BURN:
                self.energy = max(0.0, self.energy - PRECISE_ENERGY / 100.0 * self.energy_cap)
                msgs.append("Precise burn: saved propellant, used %d%% energy." % PRECISE_ENERGY)
            if self.shortfall > 0:
                msgs.append("Engines sputter - out of propellant!")
        # energy
        gen = physics.generation(self.en, g, self.turn - 1, self.base_turns) * self.solar_degrade
        gen *= self.turn_gen_mult
        if self.gen_offline > 0:
            gen = 0.0
            self.gen_offline -= 1
            msgs.append("Generator offline - no power produced.")
        load = (self.ship["load"] + self.cargo["energy"] + self.eng["power"]) * LOAD_MULT * self.route_info["power"]
        if self.power_mode == "eco":
            load *= 0.6
        self.energy = min(self.energy_cap, self.energy + gen - load)
        if self.energy <= 0:
            self.energy = 0.0
            if self.life is None:
                self.life = 100.0
                msgs.append("ENERGY DEPLETED! Life support failing - restore power NOW!")
            else:
                self.life = 0.0
                self.fail("Life support failed after the energy ran out")
        elif self.life is not None:
            self.life = None
            msgs.append("Power restored. Life support stable.")
        # food
        self.food -= self.days_per_turn * (0.7 if self.rations else 1.0)
        if self.food <= 0:
            self.food = 0.0
            self.fail("The crew ran out of food - spacecraft too small for this trip")
        self.day += self.days_per_turn
        if self.turn >= self.turns_total and self.shortfall > 1.0:
            self.fail("Out of propellant - couldn't brake into orbit at the destination")
        return msgs

    def start_experiment(self, exp_id):
        """Pay the experiment's cost. Returns the science at stake (before the challenge)."""
        e = science.EXP_BY_ID[exp_id]
        v, mult = science.experiment_value(self, exp_id)
        for k, c in e["cost"].items():
            if k == "energy":
                self.energy = max(0.0, self.energy - c)
            elif k == "fuel":
                self.fuel = max(0.0, self.fuel - c / 100.0 * self.fuel_cap)
            elif k == "food":
                self.food = max(0.0, self.food - c / 100.0 * self.food_cap)
        self.exp_counts[exp_id] = self.exp_counts.get(exp_id, 0) + 1
        self.experiments_run += 1
        self.did_experiment = True
        return v

    def finish_experiment(self, stake, correct):
        """Apply the science challenge result. Returns the science change."""
        tier = science.tier_for(stake)
        frac = science.payout(tier, correct)
        gained = round(stake * frac)
        self.science = max(0.0, self.science + gained)
        return gained

    def arrival_checks(self):
        """Atmospheric entry / extreme environment at the destination."""
        g = self.level["game"]
        need = g["entry_heat"]
        landing = self.deploy_key in ("lander", "rover")
        if need and (landing or self.level["id"] == "sun"):
            if self.a["entry_heat"] < need:
                self.fail("Burned up! Heat shield too weak for this environment (rating %d, need %d)"
                          % (self.a["entry_heat"], need))
                return
            self.shield -= 25.0 * need / self.a["entry_heat"]
            self.apply({"integrity": -6})
            if self.shield <= 0:
                self.fail("The heat shield burned through during entry")
        if self.design["engine"] == "sail" and self.a["margin"] < 0:
            self.fail("The solar sail was too weak this far from the Sun to reach the target")


# ======================================================================= scene
class MissionScene(Scene):
    music = "mission"

    def __init__(self, game):
        super().__init__(game)
        self.ms = game.mission
        self.stars = art.Starfield(seed=11)
        self.t = 0.0
        self.phase = "start"
        self.mc = MissionControl(game, (4, 20, 472, 66))
        self.popup = None
        self.panel = None   # None / 'science' / 'adjust'
        self.panel_buttons = []
        self.burning = 0.0
        self.alarm_t = 0.0
        self.started = False
        self.pending_event = None
        self.skip_warned = False
        self.alert = None
        self.alert_buttons = []
        self.buttons = [
            ui.Button((362, 205, 112, 18), "SCIENCE", self.open_science, color=BLUE, size=16),
            ui.Button((362, 226, 112, 18), "ADJUST SHIP", self.open_adjust, color=PURPLE, size=16),
            ui.Button((362, 247, 112, 18), "END TURN >", self.end_turn, color=DARKGREEN, size=16,
                      sound="select"),
        ]
        self.ship_img = pygame.transform.rotate(art.draw_ship(self.ms.design.c, flight=True), -90)
        self.ship_img = pygame.transform.scale(self.ship_img, (self.ship_img.get_width() * 2,
                                                               self.ship_img.get_height() * 2))

    def enter(self):
        super().enter()
        if not self.started:
            self.started = True
            self.mc.tip("mission_intro", [
                "Launch successful! Welcome to deep space, {name}.",
                "Each TURN is a chunk of mission time. Every turn: random events may happen, you run ONE science experiment, then END TURN.",
                "The bars at the bottom are your resources. Energy, food and fuel run down over time. Heat shield and hull only drop from damage.",
                "If ENERGY hits zero, life support starts failing. You'd have about one turn to fix it!",
            ], force=bool(self.ms.level.get("tutorial")), on_done=self.start_turn)

    # ------------------------------------------------------------ turn flow
    def start_turn(self):
        ms = self.ms
        ms.begin_turn()
        self.phase = "begin"
        self.skip_warned = False
        if ms.turn == 1 or ms.turn == ms.turns_total or ms.design["engine"] == "ion":
            self.burning = 2.0
            self.audio.play("thrust")
        # friendly alien sometimes pops in (NOT a random event)
        if ms.turn > 1 and random.random() < 0.3:
            self.popup = FactPopup(self.game, (40, 60, 400, 120))
            return
        self.after_popup()

    def after_popup(self):
        self.popup = None
        kind = self.choose_event()
        if kind:
            self.pending_event = kind
            self.phase = "event_intro"
            self.audio.play("alarm")
        else:
            self.check_alert()

    # ------------------------------------------------------------ system alerts
    def check_alert(self):
        """After any random event: maybe a ship-system alert the player must handle."""
        alert = systems.choose_alert(self.ms)
        if not alert:
            self.phase = "plan"
            self.turn_tips()
            return
        self.ms.last_alert = alert["id"]
        self.alert = alert
        self.phase = "alert"
        self.audio.play("alarm")
        self.alert_buttons = []
        opts = alert["options"]
        bw = 136 if len(opts) == 3 else 180
        x0 = W // 2 - (len(opts) * (bw + 6) - 6) // 2
        for i, (label, tip, fn, avail) in enumerate(opts):
            ok = avail(self.ms)
            self.alert_buttons.append(ui.Button((x0 + i * (bw + 6), 136, bw, 20), label,
                                                lambda fn=fn: self.resolve_alert(fn), color=PURPLE if ok else DARK,
                                                size=14, enabled=ok, tooltip=tip + ("" if ok else " [Not available]")))
        self.mc.tip("alert_intro", [
            "SYSTEMS ALERT! Small problems pop up most turns, on top of random events.",
            "Each choice has a cost: power, fuel, food, spare parts, or a risk. Hover a button to see it, then decide!",
        ], force=bool(self.ms.level.get("tutorial")) and self.ms.turn == 1)

    def resolve_alert(self, fn):
        ms = self.ms
        summary = fn(ms)
        ms.add_log(summary)
        self.alert = None
        self.alert_buttons = []
        if ms.failed:
            self.game_over()
            return
        self.phase = "plan"
        self.mc.say(summary, on_done=self.turn_tips)

    def turn_tips(self):
        ms = self.ms
        if ms.turn == 1:
            self.mc.tip("science_intro", [
                "Time for SCIENCE! Click SCIENCE and pick ONE experiment per turn. The bar at the top shows your total and what you need.",
                "Bigger experiments are worth more but end in a HARDER challenge. Repeats are worth less but are easier.",
            ], force=ms.level.get("tutorial"))
            self.mc.tip("adjust_intro", [
                "ADJUST SHIP: watch FUEL TO ARRIVE at the top. If it is more than the fuel you have, you won't make it!",
                "PRECISE BURNS save 20% propellant on every engine burn, but each burn costs energy. ECO mode, rations, emergency power and repairs are there too.",
            ], force=ms.level.get("tutorial") and ms.route == "safe")
        elif ms.turn == 2:
            self.mc.tip("adjust_intro", [
                "ADJUST SHIP: watch FUEL TO ARRIVE at the top. If it is more than the fuel you have, you won't make it!",
                "PRECISE BURNS save 20% propellant on every engine burn, but each burn costs energy. ECO mode, rations, emergency power and repairs are there too.",
            ])
        if ms.fuel_needed_pct() > ms.pct("fuel") + 0.5 and ms.design["engine"] != "sail":
            self.mc.say("WARNING: we need %d%% fuel to arrive but only have %d%%. Open ADJUST SHIP!"
                        % (ms.fuel_needed_pct(), ms.pct("fuel")))
        if ms.life is not None:
            self.mc.say("WARNING! Life support is failing. Use ECO mode or EMERGENCY POWER in ADJUST SHIP right now!")

    def choose_event(self):
        ms = self.ms
        g = ms.level["game"]
        known = len(self.game.facts.known)
        if ms.level.get("tutorial"):
            if ms.route == "safe":
                script = {3: "astronaut" if known >= 1 else None, 5: "micrometeorite"}
            else:
                script = {2: "micrometeorite", 3: random.choice(["flare", "malfunction", "asteroid"]),
                          4: "astronaut" if known >= 1 else None}
            return script.get(ms.turn)
        if ms.turn == 1 or random.random() > g["event_chance"]:
            return None
        rel = (1 - ms.eng["reliability"]) + (1 - ms.en["reliability"])
        weights = {
            "asteroid": 1.0, "micrometeorite": 1.0, "malfunction": rel * 10,
            "flare": 0.8, "pirate": 0.8 if known >= 3 else 0, "astronaut": 0.8 if known >= 1 else 0,
            "docking": 0.6 if ms.turn < ms.turns_total else 0,
        }
        for k, v in g["event_bias"].items():
            weights[k] = weights.get(k, 0) * v
        for k in list(weights):
            if ms.event_counts.get(k, 0) >= (1 if k == "docking" else 2) or k == ms.last_event:
                weights[k] = 0
        total = sum(weights.values())
        if total <= 0:
            return None
        r = random.uniform(0, total)
        for k, v in weights.items():
            r -= v
            if r <= 0:
                return k
        return None

    def launch_event(self):
        import events
        kind = self.pending_event
        self.pending_event = None
        self.ms.event_counts[kind] = self.ms.event_counts.get(kind, 0) + 1
        self.ms.last_event = kind
        self.phase = "in_event"
        self.game.switch(events.make_event(self.game, self, kind))

    def on_event_done(self, result):
        """Called by event scenes when they finish."""
        ms = self.ms
        if result.get("changes"):
            ms.apply(result["changes"])
        if result.get("fail"):
            ms.fail(result["fail"])
        if result.get("encounter"):
            ms.encounter = result["encounter"]
        if result.get("extra"):
            result["extra"](ms)
        ms.add_log(result.get("summary", "Event resolved."))
        self.game.switch(self)
        if ms.failed:
            self.game_over()
            return
        self.phase = "after_event"
        if result.get("summary"):
            self.mc.say(result["summary"], on_done=self.check_alert)
        else:
            self.check_alert()

    def end_turn(self):
        if self.phase != "plan":
            return
        ms = self.ms
        if not ms.did_experiment and not self.skip_warned:
            self.skip_warned = True
            self.mc.say("No experiment this turn! Click END TURN again if you really want to skip science.")
            return
        self.panel = None
        msgs = ms.end_turn()
        for m in msgs:
            ms.add_log(m)
        if ms.failed:
            self.game_over()
            return
        if ms.life is not None:
            self.audio.play("alarm")
        if ms.turn >= ms.turns_total:
            self.arrive()
            return
        if msgs:
            self.mc.say(msgs, on_done=self.start_turn)
        else:
            self.start_turn()

    def arrive(self):
        ms = self.ms
        ms.arrival_checks()
        if ms.failed:
            self.game_over()
            return
        if ms.level["id"] == "blackhole":
            from endings import BlackHoleChoice, first_black_hole_visit
            if first_black_hole_visit(self.game):
                self.game.switch(BlackHoleChoice(self.game))
                return
            # later visits: a science mission in a safe orbit, like any other destination
        import landing
        self.audio.play("success")
        where = "a safe orbit around the black hole" if ms.level["id"] == "blackhole" else ms.level["name"]
        if ms.dm and not ms.deploy_key:
            pts = round(15 * ms.level["game"]["science_mult"])
            ms.science += pts
            ms.dm.record(ms, pts)
            self.mc.say("We've reached %s! No payload for this stop, so we take readings during a science "
                        "fly-by: +%d science." % (where, pts), on_done=lambda: ms.dm.after_stop(self.game, ms))
            return
        from spacecraft import CARGO as _CARGO
        self.mc.say("We've arrived at %s! Time to deploy the %s." % (where, _CARGO[ms.deploy_key]["name"].lower()),
                    on_done=lambda: self.game.switch(landing.make_minigame(self.game), loading=True,
                                                     label="PREPARING DEPLOYMENT"))

    def game_over(self):
        from endings import GameOver
        self.audio.play("explosion")
        self.game.switch(GameOver(self.game))

    # ------------------------------------------------------------ panels
    def open_science(self):
        if self.phase != "plan":
            return
        if self.ms.did_experiment:
            self.mc.say("Only ONE experiment per turn. End the turn to continue.")
            return
        self.panel = "science"
        self.panel_buttons = []
        y = 60
        tier_btn = {"easy": DARKGREEN, "medium": (150, 120, 20), "hard": DARKRED}
        for e in science.EXPERIMENTS:
            ok = True
            v, mult = science.experiment_value(self.ms, e["id"], preview=True)
            tier = science.tier_for(v)
            tip = e["desc"] + "  [%s challenge] %s" % (science.tier_label(tier), science.payout_text(tier, v))
            if e.get("needs") == "encounter" and not self.ms.encounter:
                ok = False
                tip += " [No visitor encountered yet]"
            if mult < 1:
                tip += " (Repeat: %d%% value)" % (mult * 100)
            label = "%s   %d pts - %s" % (e["name"], v, science.tier_label(tier))
            self.panel_buttons.append(ui.Button((96, y, 288, 18), label,
                                                lambda i=e["id"]: self.run_experiment(i),
                                                color=tier_btn[tier], size=14, enabled=ok, tooltip=tip,
                                                sound="science"))
            y += 20
        self.panel_buttons.append(ui.Button((200, 206, 80, 16), "CLOSE", self.close_panel, color=DARK,
                                            size=14, sound="back"))

    def run_experiment(self, exp_id):
        from sciencegame import ScienceChallenge
        stake = self.ms.start_experiment(exp_id)
        self.panel = None
        self.phase = "in_science"
        self.game.switch(ScienceChallenge(self.game, self, exp_id, stake))

    def on_science_done(self, exp_id, stake, gained, correct):
        ms = self.ms
        name = science.EXP_BY_ID[exp_id]["name"]
        if gained < 0:
            ms.add_log("%s: data corrupted, %d science" % (name, gained))
        else:
            ms.add_log("%s: %d/3, +%d science" % (name, correct, gained))
        self.game.switch(self)
        self.phase = "plan"
        if ms.exp_counts[exp_id] == 2:
            self.mc.tip("diminish", "Repeats are worth less - but that also makes their challenge easier!")

    def open_adjust(self):
        if self.phase != "plan":
            return
        self.panel = "adjust"
        self.refresh_adjust()

    def refresh_adjust(self):
        ms = self.ms
        b = []
        sail = ms.design["engine"] == "sail"
        b.append(ui.Button((110, 39 + 21, 260, 18), "BURN MODE: %s" % ("SAIL" if sail else ms.burn_mode.upper()),
                           self.toggle_burn, color=ORANGE if ms.burn_mode == "precise" else PURPLE, size=14,
                           enabled=not sail,
                           tooltip="PRECISE burns use 20%% less propellant for every engine burn, but each burn "
                                   "costs %d%% energy (small course corrections are free)." % PRECISE_ENERGY))
        b.append(ui.Button((110, 81, 260, 18), "POWER MODE: %s" % ms.power_mode.upper(), self.toggle_power,
                           color=PURPLE, size=14,
                           tooltip="ECO uses 40% less energy but halves science results."))
        b.append(ui.Button((110, 102, 260, 18), "FOOD RATIONS: %s" % ("ON" if ms.rations else "OFF"),
                           self.toggle_rations, color=PURPLE, size=14,
                           tooltip="Rationing uses 30% less food but the tired crew does 15% worse science."))
        can_em = ms.fuel_cap > 0.01 and ms.design["engine"] != "sail" and not ms.used_emergency
        b.append(ui.Button((110, 123, 260, 18), "EMERGENCY POWER (-10% fuel, +30% energy)", self.emergency,
                           color=ORANGE, text_color=BLACK, size=14, enabled=can_em,
                           tooltip="Burn propellant in the fuel cells/APU. Once per turn. Fuel is needed to arrive!"))
        b.append(ui.Button((110, 144, 260, 18), "PATCH HULL (+15, spare parts: %d)" % ms.spares, self.repair,
                           color=GREY, size=14, enabled=ms.spares > 0 and not ms.used_repair,
                           tooltip="Use a spare part kit to repair structural integrity. Costs 8% energy."))
        b.append(ui.Button((200, 192, 80, 16), "CLOSE", self.close_panel, color=DARK, size=14, sound="back"))
        self.panel_buttons = b

    def toggle_burn(self):
        self.ms.burn_mode = "precise" if self.ms.burn_mode == "standard" else "standard"
        self.refresh_adjust()

    def toggle_power(self):
        self.ms.power_mode = "eco" if self.ms.power_mode == "normal" else "normal"
        self.refresh_adjust()

    def toggle_rations(self):
        self.ms.rations = not self.ms.rations
        self.refresh_adjust()

    def emergency(self):
        ms = self.ms
        ms.apply({"fuel": -10, "energy": 30})
        ms.used_emergency = True
        if ms.life is not None and ms.energy > 0:
            ms.life = None
            ms.add_log("Emergency power restored life support!")
        self.audio.play("repair")
        self.refresh_adjust()

    def repair(self):
        ms = self.ms
        ms.spares -= 1
        ms.used_repair = True
        ms.apply({"integrity": 15, "energy": -8})
        self.audio.play("repair")
        self.refresh_adjust()

    def close_panel(self):
        self.panel = None

    # ------------------------------------------------------------ events/update
    def handle(self, e):
        if self.popup:
            self.popup.handle(e)
            if self.popup.done:
                self.after_popup()
            return True
        if self.mc.handle(e):
            return True
        if self.phase == "event_intro":
            if (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1) or \
                    (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN)):
                self.launch_event()
            return True
        if self.phase == "alert":
            for b in self.alert_buttons:
                if b.handle(e, self.audio):
                    return True
            return True
        if self.panel:
            for b in self.panel_buttons:
                if b.handle(e, self.audio):
                    return True
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.panel = None
            return True
        if self.mc.active:
            return True
        return super().handle(e)

    def update(self, dt):
        self.t += dt
        self.burning = max(0.0, self.burning - dt)
        self.stars.update(dt, 50 + (120 if self.burning else 0))
        self.mc.update(dt)
        if self.popup:
            self.popup.update(dt)
        self.alarm_t += dt
        if self.ms.life is not None and self.alarm_t > 2.0:
            self.alarm_t = 0
            self.audio.play("alarm")

    # ------------------------------------------------------------ drawing
    def draw(self, s):
        ms = self.ms
        self.stars.draw(s)
        p = ms.progress()
        # Earth shrinking behind, destination growing ahead
        er = max(3, int(30 * (1 - p) ** 2))
        s.blit(art.planet(ms.level.get("from_icon", "earth"), er), (-er, 120 - er))
        dr = int(8 + 40 * p)
        dest = art.planet(ms.level["icon"], dr)
        s.blit(dest, (440 - dest.get_width() // 2, 100 - dest.get_height() // 2))
        # spacecraft
        bob = int(math.sin(self.t * 2) * 2)
        sx, sy = 110, 110 - self.ship_img.get_height() // 2 + bob
        if self.burning and int(self.t * 20) % 2 == 0:
            fl = 10 + int(math.sin(self.t * 40) * 3)
            ecol = CYAN if ms.design["engine"] == "ion" else ORANGE
            pygame.draw.rect(s, ecol, (sx - fl + 4, sy + self.ship_img.get_height() // 2 - 3, fl, 6))
            pygame.draw.rect(s, YELLOW, (sx - fl // 2 + 4, sy + self.ship_img.get_height() // 2 - 1, fl // 2, 2))
        if ms.design["engine"] == "ion" and int(self.t * 10) % 2 == 0:
            pygame.draw.rect(s, CYAN, (sx - 6, sy + self.ship_img.get_height() // 2 - 1, 8, 2))
        s.blit(self.ship_img, (sx, sy))
        if ms.integrity < 40 and int(self.t * 6) % 2 == 0:
            pygame.draw.rect(s, GREY, (sx + 20, sy + 4, 3, 3))
        # progress track
        pygame.draw.line(s, GREY, (40, 186), (440, 186))
        px = 40 + int(400 * p)
        pygame.draw.rect(s, YELLOW, (px - 2, 183, 5, 7))
        ui.text(s, ms.level.get("from_name", "Earth").upper(), (40, 174), CYAN, 14)
        ui.text(s, ms.level["name"].upper(), (440, 174), ORANGE, 14, right=True)
        # top HUD
        ui.panel(s, (0, 0, W, 18), fill=(10, 10, 28), border=GREY)
        sd = self.game.save.data
        leg = ms.level.get("leg")
        ui.text(s, "%s | %s%s | %s | TURN %d/%d | DAY %.0f" % (
            sd["player_name"], ("LEG %d/%d " % leg) if leg else "", ms.level["name"].upper(),
            ms.route_info["name"], max(ms.turn, 1), ms.turns_total, ms.day), (6, 4), YELLOW, 14)
        flags = []
        if ms.burn_mode == "precise":
            flags.append(("PRECISE", ORANGE))
        if ms.rations:
            flags.append(("RATION", ORANGE))
        if ms.power_mode == "eco":
            flags.append(("ECO", GREEN))
        fx = W - 6
        for txt, c in reversed(flags):
            fx -= ui.text(s, txt, (fx, 4), c, 14, right=True) + 6
        # science meter + fuel forecast
        need = ms.level["game"]["science_needed"]
        ui.panel(s, (0, 18, W, 16), fill=(8, 12, 34), border=BLUE)
        met = ms.science >= need
        ui.text(s, "SCIENCE", (6, 21), CYAN, 16)
        bx, bw = 62, 150
        pygame.draw.rect(s, DARK, (bx, 22, bw, 9))
        fill = int(bw * min(1.0, ms.science / max(1, need)))
        pygame.draw.rect(s, GREEN if met else CYAN, (bx, 22, fill, 9))
        pygame.draw.rect(s, GREY, (bx, 22, bw, 9), 1)
        ui.text(s, "%d / %d NEEDED%s" % (ms.science, need, "  OK!" if met else ""), (bx + bw + 6, 21),
                GREEN if met else WHITE, 16)
        if ms.design["engine"] != "sail":
            fn = ms.fuel_needed_pct()
            short = fn > ms.pct("fuel") + 0.5
            c = (RED if int(self.t * 3) % 2 == 0 else ORANGE) if short else LIGHT
            ui.text(s, "FUEL TO ARRIVE %d%% (have %d%%)" % (fn, ms.pct("fuel")), (W - 6, 22), c, 14, right=True)
        # bottom resources
        ui.panel(s, (0, 198, W, 72), fill=(10, 10, 28), border=YELLOW)
        rows = [("energy", "ENERGY", ms.pct("energy") / 100),
                ("food", "FOOD", ms.pct("food") / 100),
                ("fuel", "FUEL", ms.pct("fuel") / 100)]
        for i, (k, lab, f) in enumerate(rows):
            vt = None
            if k == "food":
                vt = "%dd" % ms.food
            if k == "fuel" and ms.design["engine"] == "sail":
                vt = "SAIL"
            ui.resource_bar(s, 6, 204 + i * 12, k, f, lab, self.t, vt)
        rows2 = [("shield", "SHIELD", ms.pct("shield") / 100),
                 ("integrity", "HULL", ms.integrity / 100),
                 ("crew", "CREW", ms.crew / 100)]
        for i, (k, lab, f) in enumerate(rows2):
            ui.resource_bar(s, 182, 204 + i * 12, k, f, lab, self.t)
        if ms.life is not None:
            ui.resource_bar(s, 182, 240, "life", ms.life / 100 * (0.5 + 0.5 * math.sin(self.t * 6)),
                            "LIFE SUP", self.t, "FAILING!")
            if ms.log:
                ui.text(s, ms.log[-1][:34], (6, 254), LIGHT, 14)
        else:
            if ms.log:
                ui.text(s, ms.log[-1][:60], (6, 242), LIGHT, 14)
            if len(ms.log) > 1:
                ui.text(s, ms.log[-2][:60], (6, 254), GREY, 14)
        if ms.did_experiment:
            ui.text(s, "Experiment done", (250, 254), GREEN, 14)
        self.draw_buttons(s, 1 / 60)
        if self.phase == "event_intro":
            names = {"asteroid": "ASTEROID FIELD AHEAD!", "micrometeorite": "MICROMETEORITE IMPACT!",
                     "malfunction": "EQUIPMENT MALFUNCTION!", "flare": "SOLAR FLARE DETECTED!",
                     "pirate": "UNKNOWN SHIP APPROACHING!", "astronaut": "DISTRESS SIGNAL RECEIVED!",
                     "docking": "SPACE STATION IN RANGE!"}
            c = RED if int(self.t * 4) % 2 == 0 else ORANGE
            ui.panel(s, (90, 70, 300, 60), fill=DARKRED, border=c)
            ui.text(s, "RANDOM EVENT", (W // 2, 78), YELLOW, 16, center=True)
            ui.text(s, names.get(self.pending_event, "?"), (W // 2, 94), WHITE, 20, center=True)
            ui.text(s, "Click to respond", (W // 2, 114), LIGHT, 14, center=True)
        if self.phase == "alert" and self.alert:
            c = ORANGE if int(self.t * 4) % 2 == 0 else YELLOW
            ui.panel(s, (34, 44, 412, 152), fill=(40, 24, 10), border=c)
            ui.text(s, "SYSTEMS ALERT: " + self.alert["title"], (W // 2, 50), YELLOW, 16, center=True)
            ui.text_block(s, self.alert["text"], (46, 66, 388, 44), WHITE, 16)
            ui.text(s, "Energy %d%%  Fuel %d%%  Food %d%%  Spare parts %d" % (
                ms.pct("energy"), ms.pct("fuel"), ms.pct("food"), ms.spares), (W // 2, 118), CYAN, 14, center=True)
            for b, opt in zip(self.alert_buttons, self.alert["options"]):
                b.draw(s, 1 / 60)
                ui.text_block(s, opt[1] if b.enabled else "Not available.",
                              (b.rect.x + 2, b.rect.bottom + 4, b.rect.w - 4, 34), LIGHT if b.enabled else GREY, 14)
            mp = pygame.mouse.get_pos()
            for b in self.alert_buttons:
                if b.rect.collidepoint(mp) and b.tooltip:
                    ui.draw_tooltip(s, b.tooltip, mp)
        if self.panel:
            title = "CHOOSE ONE EXPERIMENT" if self.panel == "science" else "SPACECRAFT ADJUSTMENTS"
            hgt = 190 if self.panel == "science" else 176
            ui.panel(s, (90, 36, 300, hgt), fill=(14, 16, 44), border=CYAN)
            ui.text(s, title, (W // 2, 39), CYAN, 16, center=True)
            if self.panel == "science":
                need = ms.level["game"]["science_needed"]
                ui.text(s, "Science %d / %d needed  -  %d turn%s left" % (
                    ms.science, need, ms.turns_total - ms.turn + 1, "" if ms.turns_total - ms.turn == 0 else "s"),
                        (W // 2, 51), YELLOW, 14, center=True)
                ui.text(s, "EASY 1-7 pts    MEDIUM 8-15    HARD 16+", (W // 2, 182), LIGHT, 14, center=True)
                ui.text(s, "Harder challenge = more risk. 0/3 loses the points!", (W // 2, 193), LIGHT, 14,
                        center=True)
            else:
                burn = ms.burn_this_turn()
                info = "This turn's engine burn: %d m/s" % burn if burn > 0 and ms.design["engine"] != "sail" \
                    else "No engine burn this turn"
                ui.text(s, info, (W // 2, 51), YELLOW, 14, center=True)
                if ms.design["engine"] != "sail":
                    ui.text(s, "Fuel to arrive: %d%% standard / %d%% precise  (have %d%%)" % (
                        ms.fuel_needed_pct(False), ms.fuel_needed_pct(True), ms.pct("fuel")), (W // 2, 168),
                            LIGHT, 14, center=True)
                ui.text(s, "Energy %d%%  (precise burn costs %d%%)" % (ms.pct("energy"), PRECISE_ENERGY),
                        (W // 2, 179), LIGHT, 14, center=True)
            for b in self.panel_buttons:
                b.draw(s, 1 / 60)
            mp = pygame.mouse.get_pos()
            for b in self.panel_buttons:
                if b.rect.collidepoint(mp) and b.tooltip:
                    ui.draw_tooltip(s, b.tooltip, mp)
        self.mc.draw(s)
        if self.popup:
            self.popup.draw(s)
