"""Ship-system alerts: small problems that crop up most turns (on top of random
events). They mostly hit the POWER system, so energy has to be actively managed.

Each alert has a title, a description and 2-3 options. An option is
(label, tooltip, effect, available) where effect(ms) applies the result and
returns a summary string, and available(ms) says whether it can be picked.
To add an alert, add a dict to ALERTS. `when(ms)` decides if it can happen.
"""
import random

ALERT_CHANCE = 0.75   # chance of a systems alert each turn (tutorial: always on turn 1)


def _always(ms):
    return True


def _has_spares(ms):
    return ms.spares > 0


def _has_fuel(ms):
    return ms.design["engine"] != "sail" and ms.fuel > 0.01


def _spend_spare(ms):
    ms.spares -= 1


# ---------------------------------------------------------------- solar panels
def _solar_rcs(ms):
    ms.apply({"fuel": -4})
    return "RCS thrusters fired. Panels face the Sun again (-4% fuel)."


def _solar_wheels(ms):
    ms.apply({"energy": -12})
    return "Reaction wheels slowly turned the ship. Panels re-aligned (-12% energy)."


def _solar_ignore(ms):
    ms.turn_gen_mult *= 0.25
    return "Panels left pointing away from the Sun: only 25% power this turn."


def _hinge_eva(ms):
    ms.apply({"energy": -10, "food": -3})
    return "Spacewalk repair! The panel wing is unfolded (-10% energy, -3% food)."


def _hinge_spare(ms):
    _spend_spare(ms)
    return "Replaced the jammed hinge motor with a spare part. Full power."


def _hinge_ignore(ms):
    ms.solar_degrade *= 0.8
    return "One panel wing stays folded: solar output is permanently 20% lower."


# ---------------------------------------------------------------- nuclear
def _reactor_reduce(ms):
    ms.turn_gen_mult *= 0.4
    return "Reactor output turned down to cool it. Only 40% power this turn."


def _reactor_vent(ms):
    ms.apply({"fuel": -5})
    return "Vented propellant through the cooling loop. Temperature normal (-5% fuel)."


def _reactor_ignore(ms):
    if random.random() < 0.55:
        ms.apply({"integrity": -12})
        ms.gen_offline = max(ms.gen_offline, 1)
        return "The reactor overheated! Hull damaged and the generator shut down for safety."
    return "Lucky! The reactor temperature settled down on its own."


def _thermo_recal(ms):
    ms.apply({"energy": -15})
    return "Thermocouples recalibrated. Output back to normal (-15% energy)."


def _thermo_ignore(ms):
    ms.solar_degrade *= 0.85
    return "The ageing thermocouples now produce 15% less power for the rest of the trip."


# ---------------------------------------------------------------- fuel cells
def _cells_reduce(ms):
    ms.turn_gen_mult *= 0.5
    return "Fuel cell output halved this turn to save reactants."


def _cells_purge(ms):
    ms.apply({"energy": -12})
    return "Cells purged and recalibrated. Reactant use is normal (-12% energy)."


def _cells_ignore(ms):
    lost = max(1.0, ms.days_total * 0.15)
    ms.en["life_days"] = max(0.0, ms.en["life_days"] - lost)
    return "Reactants burned too fast - the fuel cells will run dry %d days earlier." % lost


def _water_drink(ms):
    ms.turn_gen_mult *= 0.7
    ms.apply({"food": 6})
    return "Drained the water into the drinking supply (+6% food). Cells at 70% this turn."


def _water_vent(ms):
    ms.apply({"energy": -6})
    return "Water vented overboard. Pumps used a little power (-6% energy)."


def _water_ignore(ms):
    ms.turn_gen_mult *= 0.3
    return "Flooded cells! Only 30% power this turn."


# ---------------------------------------------------------------- any ship
def _battery_balance(ms):
    ms.apply({"energy": -8})
    return "Batteries rebalanced (-8% energy)."


def _battery_ignore(ms):
    ms.energy_cap *= 0.9
    ms.energy = min(ms.energy, ms.energy_cap)
    return "Weak cells left in place: battery capacity permanently -10%."


def _heater_spare(ms):
    _spend_spare(ms)
    return "Swapped the faulty thermostat for a spare. Heaters back to normal."


def _heater_shutdown(ms):
    ms.turn_sci_mult *= 0.5
    return "Non-essential systems switched off. Science instruments at half power this turn."


def _heater_ignore(ms):
    ms.apply({"energy": -15})
    return "Heaters ran at full blast all turn (-15% energy)."


ALERTS = [
    dict(id="solar_aim", when=lambda ms: ms.en["solar"],
         title="SOLAR PANELS OFF-SUN",
         text="The ship slowly rotated and the solar panels no longer face the Sun. "
              "Power output has dropped to 25%!",
         options=[
             ("FIRE RCS THRUSTERS", "Quick and sure, but uses 4% of your propellant.", _solar_rcs, _has_fuel),
             ("SPIN REACTION WHEELS", "No fuel, but the wheels use 12% energy.", _solar_wheels, _always),
             ("IGNORE IT", "Only 25% power this turn.", _solar_ignore, _always),
         ]),
    dict(id="solar_hinge", when=lambda ms: ms.en["solar"],
         title="PANEL HINGE JAMMED",
         text="One solar panel wing has folded up. If it is not fixed, it stays folded for the "
              "rest of the trip.",
         options=[
             ("SPACEWALK REPAIR", "Costs 10% energy and 3% food (hungry work).", _hinge_eva, _always),
             ("USE A SPARE PART", "Fixes it for free, but uses one spare part kit.", _hinge_spare, _has_spares),
             ("IGNORE IT", "Solar output permanently 20% lower.", _hinge_ignore, _always),
         ]),
    dict(id="reactor_hot", when=lambda ms: ms.design["energy"] == "nuclear",
         title="REACTOR RUNNING HOT",
         text="The nuclear power source is getting too hot. Cooling it costs power or propellant. "
              "Ignoring it is a gamble.",
         options=[
             ("REDUCE OUTPUT", "Safe, but only 40% power this turn.", _reactor_reduce, _always),
             ("VENT COOLANT", "Normal power, but uses 5% of your propellant.", _reactor_vent, _has_fuel),
             ("IGNORE IT", "Over 50% chance of hull damage and a generator shutdown.", _reactor_ignore, _always),
         ]),
    dict(id="reactor_thermo", when=lambda ms: ms.design["energy"] == "nuclear",
         title="THERMOCOUPLES DRIFTING",
         text="The parts that turn reactor heat into electricity are drifting out of calibration.",
         options=[
             ("RECALIBRATE", "Costs 15% energy now.", _thermo_recal, _always),
             ("IGNORE IT", "Power output permanently 15% lower.", _thermo_ignore, _always),
         ]),
    dict(id="cells_hot", when=lambda ms: ms.design["energy"] == "fuelcell",
         title="FUEL CELLS RUNNING HOT",
         text="The fuel cells are overheating and burning through their reactants much too fast.",
         options=[
             ("REDUCE OUTPUT", "Only 50% power this turn, saves reactants.", _cells_reduce, _always),
             ("PURGE & RECALIBRATE", "Costs 12% energy now.", _cells_purge, _always),
             ("IGNORE IT", "The cells run dry noticeably earlier.", _cells_ignore, _always),
         ]),
    dict(id="cells_water", when=lambda ms: ms.design["energy"] == "fuelcell",
         title="WATER BUILD-UP IN FUEL CELLS",
         text="Fuel cells make water as they run. It is flooding the cells and must go somewhere.",
         options=[
             ("DRAIN TO DRINKING TANKS", "+6% food (water), but cells run at 70% this turn.", _water_drink, _always),
             ("VENT OVERBOARD", "Costs 6% energy for the pumps.", _water_vent, _always),
             ("IGNORE IT", "Only 30% power this turn.", _water_ignore, _always),
         ]),
    dict(id="battery", when=_always,
         title="BATTERY CELL IMBALANCE",
         text="Some battery cells are draining faster than others. Left alone, they'll be ruined.",
         options=[
             ("REBALANCE", "Costs 8% energy now.", _battery_balance, _always),
             ("IGNORE IT", "Battery capacity permanently 10% lower.", _battery_ignore, _always),
         ]),
    dict(id="heaters", when=_always,
         title="HEATERS STUCK ON",
         text="A thermostat failed and the cabin heaters are running at full power.",
         options=[
             ("USE A SPARE PART", "Fixes it, but uses one spare part kit.", _heater_spare, _has_spares),
             ("SWITCH OFF NON-ESSENTIALS", "Science gives half results this turn.", _heater_shutdown, _always),
             ("IGNORE IT", "Costs 15% energy.", _heater_ignore, _always),
         ]),
]
ALERT_BY_ID = {a["id"]: a for a in ALERTS}


def choose_alert(ms):
    """Pick this turn's alert (or None). Power-system alerts are twice as likely."""
    forced = ms.level.get("tutorial") and ms.turn == 1
    if not forced and random.random() > ALERT_CHANCE:
        return None
    pool = [a for a in ALERTS if a["when"](ms) and a["id"] != ms.last_alert]
    if forced:
        pool = [a for a in pool if a["id"] not in ("battery", "heaters")] or pool
    if not pool:
        return None
    weights = [1.0 if a["id"] in ("battery", "heaters") else 2.0 for a in pool]
    return random.choices(pool, weights=weights)[0]
