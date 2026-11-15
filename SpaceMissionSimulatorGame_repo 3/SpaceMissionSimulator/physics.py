"""Simplified (but real) rocket physics.

Uses the Tsiolkovsky rocket equation  dv = Isp * g0 * ln(m0 / mf)  for each stage,
thrust-to-weight ratio for lift-off, a gravity-loss penalty for low TWR,
and simple models for heating, structural load (Max-Q), power, and food.
"""
import math
from spacecraft import (LV_SIZES, MATERIALS, BOOSTERS, SHIPS, SHIELDS, ENGINES,
                        ENERGY, CARGO)

G0 = 9.80665              # m/s^2, standard gravity
ORBIT_DV = 9400.0         # m/s to reach low Earth orbit incl. typical drag/gravity losses
ORBIT_SPEED = 7.8         # km/s, low Earth orbit speed
EARTH_ESCAPE = 11.2       # km/s
ASCENT_HEAT_NEED = 45     # heat rating needed to survive ascent heating
MIN_TWR = 1.15            # below this the rocket can't climb away from the pad
SAIL_DV_1AU = 25000.0     # m/s a solar sail can accumulate over a mission at 1 AU

# Where a rocket can launch from (Design Mission can start on any solid body).
# g: surface gravity m/s^2, orbit_dv: m/s to reach low orbit incl. losses,
# orbit_speed / escape: km/s, heat_need: ascent heating, air: has an atmosphere (Max-Q).
LAUNCH_SITES = {
    "earth": dict(name="Earth", g=9.81, orbit_dv=ORBIT_DV, orbit_speed=ORBIT_SPEED, escape=EARTH_ESCAPE,
                  heat_need=ASCENT_HEAT_NEED, air=1.0),
    "moon": dict(name="the Moon", g=1.62, orbit_dv=1900.0, orbit_speed=1.68, escape=2.38, heat_need=0, air=0.0),
    "mars": dict(name="Mars", g=3.71, orbit_dv=4100.0, orbit_speed=3.55, escape=5.03, heat_need=15, air=0.3),
    "asteroid": dict(name="Bennu", g=0.0001, orbit_dv=5.0, orbit_speed=0.0001, escape=0.0002, heat_need=0,
                     air=0.0),
}


def launch_site(level):
    return LAUNCH_SITES[level["game"].get("launch", "earth")]


def rocket_dv(isp, m0, mf):
    if mf <= 0 or m0 <= mf or isp <= 0:
        return 0.0
    return isp * G0 * math.log(m0 / mf)


def fuel_for_dv(isp, m_start, dv):
    """Propellant (t) needed to give mass m_start a velocity change dv."""
    if isp <= 0:
        return float("inf")
    return m_start * (1.0 - math.exp(-dv / (isp * G0)))


def ship_masses(d):
    ship, eng = SHIPS[d["ship"]], ENGINES[d["engine"]]
    shield = SHIELDS[d["shield"]]
    dry = (ship["dry"] + shield["mass"] * ship["area"] + eng["mass"]
           + ENERGY[d["energy"]]["mass"] + CARGO[d["cargo"]]["mass"])
    fuel = ship["fuel"] * eng["fuel_factor"]
    return dry, fuel


def heat_rating(d):
    mat = MATERIALS[d["material"]]
    sh = SHIELDS[d["shield"]]
    return 0.4 * mat["heat"] + 0.6 * sh["heat"]


def entry_rating(d):
    """Atmospheric entry heating is taken mostly by the heat shield."""
    return 0.2 * MATERIALS[d["material"]]["heat"] + 0.8 * SHIELDS[d["shield"]]["heat"]


def strength_rating(d):
    return 0.5 * MATERIALS[d["material"]]["strength"] + 0.5 * SHIPS[d["ship"]]["strength"]


def sail_dv(level):
    g = level["game"]
    r = max(0.05, (g["au_start"] + g["au_end"]) / 2.0)
    # Sunlight pressure falls with 1/r^2; inward missions use it best.
    return SAIL_DV_1AU * min(2.0, 1.0 / (r * r)) if g["au_end"] <= 1.6 else SAIL_DV_1AU / (r * r)


def travel_days(d, level):
    eng = ENGINES[d["engine"]]
    t = eng["time"]
    if d["engine"] == "sail" and level["game"]["au_end"] < 1.0:
        t = 1.15  # sails fall sunward quickly
    return level["game"]["days"] * t


def solar_eff(au):
    return min(1.6, 1.0 / max(0.05, au) ** 2)


def au_at(g, turn, turns):
    f = turn / max(1, turns - 1)
    return g["au_start"] + (g["au_end"] - g["au_start"]) * f


def generation(en, g, turn, turns):
    """Energy produced in a given turn (before malfunctions)."""
    if turn * g["days"] / max(1, turns) >= en["life_days"]:
        return 0.0
    if en["solar"]:
        return en["output"] * solar_eff(au_at(g, turn, turns))
    return en["output"]


def analyze(d, level):
    """Full performance analysis of a complete design for a mission."""
    g = level["game"]
    site = launch_site(level)
    size, mat, boo = LV_SIZES[d["lv_size"]], MATERIALS[d["material"]], BOOSTERS[d["booster"]]
    ship, eng = SHIPS[d["ship"]], ENGINES[d["engine"]]
    en, cargo = ENERGY[d["energy"]], CARGO[d["cargo"]]

    dry, fuel = ship_masses(d)
    ship_wet = dry + fuel
    lv_struct = size["structure"] * mat["mass"]
    lv_eng = size["engine_mass"] * boo["mass"]
    lv_fuel = size["fuel"]
    m0 = lv_struct + lv_eng + lv_fuel + ship_wet
    thrust = size["thrust"] * boo["thrust"]
    twr = thrust / (m0 * max(0.01, site["g"]))

    # Two internal stages: 72% of fuel / 70% of dry mass in stage 1.
    f1, f2 = lv_fuel * 0.72, lv_fuel * 0.28
    d1 = (lv_struct + lv_eng) * 0.70
    d2 = (lv_struct + lv_eng) * 0.30
    dv1 = rocket_dv(boo["isp_sl"], m0, m0 - f1)
    m_after1 = m0 - f1 - d1
    dv2 = rocket_dv(boo["isp_vac"], m_after1, m_after1 - f2)
    lv_dv = dv1 + dv2 if twr >= MIN_TWR else 0.0

    grav_loss = 0.0
    if 0 < twr < 1.5:
        grav_loss = 1500.0 * (1.5 / twr - 1.0) * site["g"] / G0
    orbit_need = site["orbit_dv"] + grav_loss

    # Spacecraft delta-v
    if d["engine"] == "sail":
        ship_dv = sail_dv(level)
    else:
        ship_dv = rocket_dv(eng["isp"], ship_wet, dry)

    transfer = g["transfer_dv"]
    # Launch vehicle surplus can do the departure burn (like Saturn V's S-IVB)
    # but the spacecraft must always do its own arrival / capture burn.
    orbit_deficit = max(0.0, orbit_need - lv_dv)
    surplus = max(0.0, lv_dv - orbit_need)
    ship_transfer = max(0.30 * transfer, transfer - surplus)
    ship_transfer += g.get("extra_dv", 0.0)   # Design Mission: later legs are flown by the spacecraft alone
    ship_needed = orbit_deficit + ship_transfer
    if orbit_deficit > 0 and not eng["high_thrust"]:
        reach_orbit = False
    else:
        reach_orbit = (lv_dv > 0) and (ship_dv >= orbit_deficit)
    margin = ship_dv - ship_needed
    after_orbit = max(0.0, lv_dv - orbit_need) + max(0.0, ship_dv - orbit_deficit)
    max_vel = site["orbit_speed"] + after_orbit / 1000.0

    heat = heat_rating(d)
    strength = strength_rating(d)
    maxq_need = (50 + 30 * max(0.0, twr - 1.4) + (10 if m0 > 3000 else 0)) * site["air"]

    days = travel_days(d, level)
    food_ok = ship["food_days"] >= days
    turns = g["turns"]
    load = ship["load"] + cargo["energy"] + eng["power"]
    gen_start = generation(en, g, 0, turns)
    total_gen = sum(generation(en, g, t, turns) for t in range(turns))
    energy_ok = en["storage"] + total_gen - turns * load * 1.0 >= 0

    cargo_fits = cargo["mass"] <= ship["cargo_cap"]
    cargo_allowed = d["cargo"] in g["allowed_cargo"]
    entry_heat = entry_rating(d)
    entry_ok = entry_heat >= g["entry_heat"] if g["entry_heat"] else True

    return dict(
        mass=m0, ship_mass=ship_wet, ship_dry=dry, ship_fuel=fuel, thrust=thrust, twr=twr,
        lv_dv=lv_dv, ship_dv=ship_dv, orbit_need=orbit_need, transfer=transfer,
        ship_needed=ship_needed, ship_transfer=ship_transfer, orbit_deficit=orbit_deficit,
        margin=margin, max_vel=max_vel, heat=heat, entry_heat=entry_heat, strength=strength, maxq_need=maxq_need,
        days=days, food_days=ship["food_days"], food_ok=food_ok, energy_gen=gen_start, energy_load=load,
        energy_ok=energy_ok, cargo_cap=ship["cargo_cap"], cargo_fits=cargo_fits,
        cargo_allowed=cargo_allowed, reach_orbit=reach_orbit, entry_ok=entry_ok,
        heat_need=site["heat_need"], escape_need=site["escape"], orbit_speed=site["orbit_speed"],
        site=site["name"],
        cost=None,
    )


def predicted_failures(a):
    """List of (stage, reason) a design will hit. Used for balance checks and warnings."""
    out = []
    if a["twr"] < MIN_TWR:
        out.append(("liftoff", "Thrust-to-weight ratio %.2f is too low to lift off" % a["twr"]))
        return out
    if a["strength"] < a["maxq_need"]:
        out.append(("maxq", "Structure too weak for Max-Q aerodynamic stress"))
    if a["heat"] < a["heat_need"]:
        out.append(("heat", "Burned up: heat resistance too low for ascent"))
    if not a["reach_orbit"]:
        out.append(("orbit", "Not enough delta-v to reach orbit"))
    if a["max_vel"] < a["escape_need"]:
        out.append(("escape", "Could not reach escape velocity from %s" % a["site"]))
    if a["margin"] < 0:
        out.append(("fuel", "Ran out of propellant before arrival"))
    if not a["food_ok"]:
        out.append(("food", "Not enough food storage for the journey"))
    if not a["energy_ok"]:
        out.append(("energy", "Power system can't keep life support running"))
    if not a["entry_ok"]:
        out.append(("entry", "Heat shield too weak for atmospheric entry"))
    return out
