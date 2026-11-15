"""Build-screen explanations.

When a design has a problem we explain WHAT the problem means, the player's
actual numbers, and WHICH parts influence it - but we never say which option
to pick. Finding the right combination is still the player's job.
"""
import physics

# What each kind of part influences (shown in the option tooltips).
AFFECTS = {
    "lv_size": "Affects: launch fuel (delta-v to orbit), lift-off thrust, total mass and cost.",
    "material": "Affects: launch vehicle mass (TWR and delta-v), heat resistance (40% of HEAT RES) "
                "and structural strength (Max-Q).",
    "ship": "Affects: spacecraft fuel tanks and dry mass (spacecraft delta-v), food days, cargo bay, "
            "strength, power use and shield area.",
    "shield": "Affects: heat resistance (60% of HEAT RES, 80% of entry heating), shield durability, "
              "and mass (heavier shields cost spacecraft delta-v).",
    "booster": "Affects: lift-off thrust (TWR) and launch efficiency (Isp = delta-v to reach orbit).",
    "engine": "Affects: spacecraft efficiency (Isp = delta-v from the same fuel), trip time, "
              "engine mass and power use.",
    "energy": "Affects: power produced each turn, battery storage, mass, and how far from the Sun "
              "it keeps working.",
    "cargo": "Affects: mission objective, science, power use and mass carried by the spacecraft.",
}

# stage -> (title, explanation of the physics, which parts influence it)
HELP = {
    "liftoff": (
        "THRUST-TO-WEIGHT TOO LOW",
        "TWR = lift-off thrust / weight of the WHOLE rocket. Below 1.15 it can't climb off the pad, "
        "and below 1.5 it wastes fuel fighting gravity (gravity losses).",
        "Thrust comes from the launch vehicle SIZE and the launch vehicle ENGINE type. "
        "Weight comes from everything you stack up: the launch vehicle material and fuel, the "
        "spacecraft, its shield, engine, power system and cargo.",
    ),
    "maxq": (
        "STRUCTURE TOO WEAK FOR MAX-Q",
        "Max-Q is the moment of greatest air pressure on the rocket during ascent. "
        "STRENGTH = average of the launch vehicle material's strength and the spacecraft's strength.",
        "A more violent ascent (TWR above 1.4) and very heavy rockets (over 3000 t) raise the "
        "strength needed. So both the strength of your parts AND how hard you push matter.",
    ),
    "heat": (
        "HEAT RESISTANCE TOO LOW FOR ASCENT",
        "Air friction heats the rocket on the way up. HEAT RES = 40%% launch vehicle material + "
        "60%% heat shield. The ascent needs at least %d." % physics.ASCENT_HEAT_NEED,
        "Each material and shield has its own heat rating (hover them to compare). "
        "Better heat protection is usually heavier or more expensive.",
    ),
    "orbit": (
        "NOT ENOUGH DELTA-V TO REACH ORBIT",
        "Delta-v is the total change in speed a rocket can make. Rocket equation: "
        "dv = Isp x 9.81 x ln(full mass / empty mass). Orbit needs about 9.4 km/s plus any gravity losses.",
        "The launch vehicle's delta-v goes UP with more fuel and a higher-Isp (more efficient) engine, "
        "and goes DOWN with every tonne it has to carry: its own structure and everything on top. "
        "If it falls short, only a high-thrust spacecraft engine can finish the job.",
    ),
    "escape": (
        "CAN'T REACH EARTH ESCAPE VELOCITY",
        "MAX VEL = 7.8 km/s orbital speed + all the delta-v left after reaching orbit. "
        "It must beat Earth's escape velocity of 11.2 km/s.",
        "Spare delta-v comes from a launch vehicle with surplus, plus the spacecraft's own delta-v "
        "(its fuel, its engine's Isp, and how light it is when empty).",
    ),
    "fuel": (
        "SPACECRAFT RUNS OUT OF PROPELLANT",
        "After leaving Earth the spacecraft must do its own burns to reach and brake at the target. "
        "Its delta-v = Isp x 9.81 x ln(full mass / empty mass).",
        "More delta-v comes from: bigger fuel tanks (spacecraft type), a more efficient engine "
        "(higher Isp), or a lighter empty ship (shield, engine, power system and cargo all add mass). "
        "Surplus from the launch vehicle can also do part of the departure burn.",
    ),
    "food": (
        "NOT ENOUGH FOOD FOR THE TRIP",
        "The crew eats every day. The trip length depends on the destination AND on how fast your "
        "engine gets you there.",
        "Food storage depends on the spacecraft type. Slow, efficient engines make the trip longer; "
        "fast engines make it shorter. Your route choice later will also change the trip length.",
    ),
    "energy": (
        "POWER SYSTEM CAN'T KEEP UP",
        "Every turn the ship uses power (life support, computers, cargo, electric engines). "
        "The power system must produce enough, plus battery storage to cover gaps.",
        "Solar output falls with 1/distance^2 from the Sun. Fuel cells stop after ~40 days. "
        "Nuclear works anywhere. Bigger ships, power-hungry cargo and electric engines use more.",
    ),
    "entry": (
        "HEAT SHIELD TOO WEAK FOR ENTRY",
        "Entering an atmosphere (or flying close to the Sun) is far hotter than launch. "
        "Entry rating = 20% material + 80% heat shield.",
        "The heat shield matters most here. Check the destination briefing for how harsh it is.",
    ),
    "thin": (
        "DELTA-V MARGIN IS VERY THIN",
        "Your ship can just about make it, but there is almost no spare fuel.",
        "Random events, a longer route or a fuel leak could leave you stranded. "
        "Extra margin comes from the same things that give delta-v: fuel, Isp and low mass.",
    ),
}


def numbers(stage, a, level):
    """Short line with the player's actual numbers for this problem."""
    g = level["game"]
    if stage == "liftoff":
        return "Your TWR: %.2f (need 1.15+, 1.5+ avoids gravity losses)" % a["twr"]
    if stage == "maxq":
        return "Your strength: %.0f  -  needed: %.0f" % (a["strength"], a["maxq_need"])
    if stage == "heat":
        return "Your heat resistance: %.0f  -  needed: %d" % (a["heat"], a["heat_need"])
    if stage == "orbit":
        return "Launch vehicle dV: %.1f km/s  -  orbit needs: %.1f km/s" % (a["lv_dv"] / 1000,
                                                                          a["orbit_need"] / 1000)
    if stage == "escape":
        return "Your max velocity: %.1f km/s  -  escape from %s needs: %.1f km/s" % (
            a["max_vel"], a["site"], a["escape_need"])
    if stage in ("fuel", "thin"):
        return "Spacecraft dV: %.1f km/s  -  needed: %.1f km/s  (margin %+d m/s)" % (
            a["ship_dv"] / 1000, a["ship_needed"] / 1000, a["margin"])
    if stage == "food":
        return "Trip: %d days  -  food stored: %d days" % (a["days"], a["food_days"])
    if stage == "energy":
        return "Generation now: %.1f/turn  -  ship uses: %.1f/turn" % (a["energy_gen"], a["energy_load"])
    if stage == "entry":
        return "Your entry rating: %.0f  -  needed: %d" % (a["entry_heat"], g["entry_heat"])
    return ""
