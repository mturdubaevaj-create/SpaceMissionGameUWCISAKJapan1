"""Mission / destination database.

`real` holds real-world physical properties (shown to the player as facts).
`game` holds simplified game-mechanics values (budgets, delta-v needs, turns).
To add a new destination, add an entry here (and an icon kind in art.py).
"""

LEVELS = [
    dict(
        id="moon", name="The Moon", icon="moon", tutorial=True,
        real=dict(
            temp="-173 C (night) to 127 C (day)",
            gravity="1.62 m/s^2 (about 1/6 of Earth)",
            escape="2.38 km/s",
            atmosphere="None (a near-vacuum exosphere)",
            distance="384,400 km from Earth",
            hazards="Vacuum, huge temperature swings, sharp regolith dust",
        ),
        game=dict(
            budget=950, transfer_dv=3900, days=3, turns=5, au_start=1.0, au_end=1.0,
            allowed_cargo=["lander"], entry_heat=0, landing_g=1.62,
            science_needed=80, science_mult=1.0, event_chance=0.6,
            event_bias={},
            dv_note="Trans-lunar injection (~3.1 km/s) + lunar orbit insertion (~0.8 km/s)",
        ),
        objective="Land the lander upright on the Moon.",
    ),
    dict(
        id="mars", name="Mars", icon="mars",
        real=dict(
            temp="-125 C to 20 C (average about -63 C)",
            gravity="3.71 m/s^2 (38% of Earth)",
            escape="5.03 km/s",
            atmosphere="Thin CO2 (95%), under 1% of Earth's pressure",
            distance="55 to 400 million km (changes with orbits)",
            hazards="Dust storms, radiation, thin air makes landing hard",
        ),
        game=dict(
            budget=1300, transfer_dv=4300, days=210, turns=9, au_start=1.0, au_end=1.52,
            allowed_cargo=["lander", "rover"], entry_heat=55, landing_g=3.71,
            science_needed=130, science_mult=1.3, event_chance=0.65,
            event_bias={"flare": 1.2},
            dv_note="Trans-Mars injection (~3.6 km/s) + capture, helped by aerobraking",
        ),
        objective="Deliver a lander or rover safely to the Martian surface.",
    ),
    dict(
        id="venus", name="Venus", icon="venus",
        real=dict(
            temp="About 465 C - the hottest planet!",
            gravity="8.87 m/s^2 (90% of Earth)",
            escape="10.36 km/s",
            atmosphere="96.5% CO2, 92x Earth pressure, sulfuric acid clouds",
            distance="38 to 261 million km",
            hazards="Crushing pressure, acid clouds, extreme heat",
        ),
        game=dict(
            budget=1250, transfer_dv=3900, days=150, turns=8, au_start=1.0, au_end=0.72,
            allowed_cargo=["satellite"], entry_heat=0, landing_g=8.87,
            science_needed=130, science_mult=1.3, event_chance=0.65,
            event_bias={"flare": 1.5},
            dv_note="Trans-Venus injection (~3.5 km/s) + capture with aerobraking",
        ),
        objective="Put a satellite into the correct orbit around Venus.",
    ),
    dict(
        id="jupiter", name="Jupiter", icon="jupiter",
        real=dict(
            temp="About -110 C at the cloud tops",
            gravity="24.79 m/s^2 (2.5x Earth)",
            escape="59.5 km/s",
            atmosphere="Hydrogen and helium gas giant, no solid surface",
            distance="588 to 968 million km",
            hazards="The deadliest radiation belts in the Solar System",
        ),
        game=dict(
            budget=2000, transfer_dv=6800, days=900, turns=11, au_start=1.0, au_end=5.2,
            allowed_cargo=["satellite", "lab"], entry_heat=0, landing_g=24.79,
            science_needed=160, science_mult=1.6, event_chance=0.7,
            event_bias={"asteroid": 1.6},
            dv_note="Trans-Jupiter injection (~6.3 km/s) + orbit insertion",
        ),
        objective="Insert an orbiter (satellite or lab) around Jupiter.",
    ),
    dict(
        id="saturn", name="Saturn", icon="saturn",
        real=dict(
            temp="About -140 C at the cloud tops",
            gravity="10.44 m/s^2",
            escape="35.5 km/s",
            atmosphere="Hydrogen and helium, less dense than water!",
            distance="1.2 to 1.7 billion km",
            hazards="Ring particles, long journey, very little sunlight",
        ),
        game=dict(
            budget=2300, transfer_dv=7800, days=1500, turns=12, au_start=1.0, au_end=9.5,
            allowed_cargo=["satellite", "telescope", "lab"], entry_heat=0, landing_g=10.44,
            science_needed=175, science_mult=1.8, event_chance=0.7,
            event_bias={"asteroid": 1.8},
            dv_note="Trans-Saturn injection (~7.3 km/s) + orbit insertion",
        ),
        objective="Deploy an orbiter or telescope at Saturn.",
    ),
    dict(
        id="sun", name="The Sun", icon="sun",
        real=dict(
            temp="About 5,500 C surface, over 1,000,000 C corona",
            gravity="274 m/s^2 (28x Earth)",
            escape="617.7 km/s",
            atmosphere="Hot plasma: hydrogen and helium",
            distance="About 150 million km (1 AU)",
            hazards="Extreme heat and radiation, constant solar flares",
        ),
        game=dict(
            budget=2600, transfer_dv=12000, days=180, turns=10, au_start=1.0, au_end=0.05,
            allowed_cargo=["telescope", "satellite"], entry_heat=85, landing_g=274,
            science_needed=200, science_mult=1.9, event_chance=0.75,
            event_bias={"flare": 3.0},
            dv_note="Game value: shedding Earth's orbital speed using Venus gravity assists",
        ),
        objective="Fly close to the Sun and deploy a solar telescope or probe.",
    ),
    dict(
        id="asteroid", name="Asteroid Bennu", icon="bennu",
        real=dict(
            temp="Varies widely between day and night side",
            gravity="Tiny: about 0.00008 m/s^2",
            escape="About 0.2 m/s - you could jump off it!",
            atmosphere="None",
            distance="Near-Earth asteroid, OSIRIS-REx took ~2 years",
            hazards="Rubble surface, boulders, dust, asteroid swarms",
        ),
        game=dict(
            budget=1700, transfer_dv=5200, days=420, turns=10, au_start=1.0, au_end=1.1,
            allowed_cargo=["lander", "rover"], entry_heat=0, landing_g=0.15,
            science_needed=175, science_mult=1.7, event_chance=0.8,
            event_bias={"asteroid": 3.0, "micrometeorite": 1.5},
            dv_note="Rendezvous with Bennu (game-simplified)",
        ),
        objective="Touch down on Bennu (landing gravity is game-scaled).",
    ),
    dict(
        id="blackhole", name="Black Hole", icon="blackhole", final=True,
        real=dict(
            temp="Fictional target. Accretion disks reach millions of C",
            gravity="Unimaginable near the event horizon",
            escape="Equal to the speed of light at the event horizon",
            atmosphere="None. Spacetime itself is warped",
            distance="Nearest known: Gaia BH1, ~1,560 light-years away",
            hazards="Tidal forces, time dilation, no way back!",
        ),
        game=dict(
            budget=3600, transfer_dv=8000, days=800, turns=12, au_start=1.0, au_end=9.5,
            allowed_cargo=["lab"], entry_heat=0, landing_g=0,
            science_needed=0, science_mult=2.5, event_chance=0.8,
            event_bias={"asteroid": 1.5, "flare": 1.2},
            dv_note="SCIENCE FICTION: reach a wormhole near Saturn that leads to the black hole",
        ),
        objective="Carry a laboratory to the black hole... and beyond.",
    ),
]

LEVEL_BY_ID = {lv["id"]: lv for lv in LEVELS}
ORDER = [lv["id"] for lv in LEVELS]


def next_level(level_id):
    i = ORDER.index(level_id)
    return ORDER[i + 1] if i + 1 < len(ORDER) else None
