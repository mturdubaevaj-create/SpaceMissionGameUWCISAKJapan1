"""Spacecraft component database and the Design class.

Every component is plain data, so adding a new one is just adding a dict entry.
Masses are in tonnes, costs in millions of dollars ($M), thrust in kN,
specific impulse (Isp) in seconds. Ratings (heat, strength...) are 0-100
game ratings.
"""

# ---------------------------------------------------------------- launch vehicle
# A launch vehicle is modelled internally as a two-stage booster stack.
LV_SIZES = {
    "S": dict(name="Small (S)", structure=60, fuel=1100, engine_mass=12,
              thrust=16000, cost=150, engine_cost=60, w=14, h=52,
              desc="Light, cheap booster stack. Only for light spacecraft."),
    "M": dict(name="Medium (M)", structure=100, fuel=2200, engine_mass=22,
              thrust=30000, cost=260, engine_cost=100, w=18, h=66,
              desc="Balanced workhorse booster. Enough for most Moon missions."),
    "L": dict(name="Large (L)", structure=160, fuel=3800, engine_mass=36,
              thrust=52000, cost=420, engine_cost=150, w=22, h=82,
              desc="Huge Saturn V class stack. Lifts heavy, long-range ships."),
}

MATERIALS = {
    "aluminium": dict(name="Aluminium", mass=1.00, cost=1.00, heat=30, strength=55,
                      color=(200, 202, 214), dark=(150, 150, 168),
                      desc="Light and cheap but melts easily. Poor heat resistance."),
    "titanium": dict(name="Titanium", mass=1.25, cost=1.90, heat=70, strength=75,
                     color=(150, 156, 176), dark=(104, 108, 128),
                     desc="Strong and very heat resistant, but expensive."),
    "steel": dict(name="Stainless steel", mass=1.60, cost=0.80, heat=62, strength=90,
                  color=(222, 226, 236), dark=(160, 166, 180),
                  desc="Cheap, tough and heat tolerant - but very heavy."),
    "carbon": dict(name="Carbon composite", mass=0.72, cost=2.30, heat=38, strength=72,
                   color=(70, 70, 84), dark=(40, 40, 52),
                   desc="Ultra light and strong. Pricey, weak against heat."),
}

# Engines for the launch vehicle (nuclear and solar sail are NOT allowed here).
BOOSTERS = {
    "solid": dict(name="Solid rocket", thrust=1.30, isp_sl=250, isp_vac=285, mass=1.4,
                  cost=0.5, reliability=0.93,
                  desc="Huge thrust, cheap, simple. Low efficiency, can't throttle."),
    "liquid": dict(name="Liquid rocket", thrust=1.00, isp_sl=300, isp_vac=420, mass=1.0,
                   cost=1.0, reliability=0.97,
                   desc="Efficient and throttleable. Costs more."),
    "ion": dict(name="Ion thruster", thrust=0.0002, isp_sl=2000, isp_vac=3000, mass=0.3,
                cost=1.6, reliability=0.98,
                desc="Super efficient but almost zero thrust. Can it lift off?"),
}

# ---------------------------------------------------------------- spacecraft
SHIPS = {
    "shuttle": dict(name="Shuttle", dry=14, fuel=30, food_days=30, cargo_cap=8,
                    strength=60, cost=120, load=3.0, area=1.0, spares=1,
                    storm_shelter=False,
                    desc="Compact and cheap. Small cargo bay, food for ~30 days."),
    "heavy": dict(name="Heavy ship", dry=32, fuel=80, food_days=300, cargo_cap=30,
                  strength=85, cost=260, load=5.0, area=1.6, spares=3,
                  storm_shelter=False,
                  desc="Saturn V style giant. Big fuel tanks and cargo bay."),
    "longrange": dict(name="Long-range ship", dry=42, fuel=90, food_days=1800,
                      cargo_cap=16, strength=70, cost=420, load=6.0, area=2.0,
                      spares=2, storm_shelter=True,
                      desc="Endurance-style ring ship. Years of food + storm shelter."),
    "station": dict(name="Interplanetary station", dry=40, fuel=300, food_days=6000, cargo_cap=60,
                    strength=80, cost=900, load=2.5, area=2.6, spares=4, storm_shelter=True,
                    design_only=True,
                    desc="DESIGN MISSION ONLY. Huge, costly station that carries one payload per stop."),
}

# Heat shield values are per unit of ship surface 'area'.
SHIELDS = {
    "blanket": dict(name="Thermal blanket", mass=0.4, cost=8, heat=30, durability=40,
                    color=(222, 184, 64),
                    desc="Gold foil insulation. Feather light, minimal protection."),
    "cork": dict(name="Cork ablator", mass=1.2, cost=25, heat=58, durability=60,
                 color=(150, 104, 64),
                 desc="Burns away slowly to carry heat off. Cheap and decent."),
    "ceramic": dict(name="Ceramic tiles", mass=2.2, cost=55, heat=74, durability=80,
                    color=(40, 40, 46),
                    desc="Space Shuttle style tiles. Reusable, heavy-ish."),
    "pica": dict(name="PICA-X", mass=1.8, cost=100, heat=92, durability=95,
                 color=(70, 46, 34),
                 desc="Top-tier ablator (used on Dragon). Survives extreme heat."),
}

# Engines for the spacecraft itself.
ENGINES = {
    "solid": dict(name="Solid motor", mass=2.5, cost=30, thrust=900, isp=275,
                  fuel_factor=1.0, time=1.0, power=0, reliability=0.92, high_thrust=True,
                  desc="Big kick, low efficiency. Simple and cheap."),
    "liquid": dict(name="Liquid engine", mass=3.5, cost=80, thrust=650, isp=350,
                   fuel_factor=1.0, time=1.0, power=0, reliability=0.96, high_thrust=True,
                   desc="Reliable, efficient chemical engine."),
    "ion": dict(name="Ion drive", mass=1.5, cost=200, thrust=0.5, isp=3100,
                fuel_factor=0.35, time=1.5, power=8, reliability=0.97, high_thrust=False,
                desc="10x efficiency, tiny thrust: slow trips, needs lots of power."),
    "nuclear": dict(name="Nuclear thermal", mass=8.0, cost=420, thrust=330, isp=900,
                    fuel_factor=1.0, time=0.6, power=1, reliability=0.94, high_thrust=True,
                    desc="Reactor-heated hydrogen. Fast trips, heavy, very costly."),
    "sail": dict(name="Solar sail", mass=1.0, cost=360, thrust=0.0, isp=0,
                 fuel_factor=0.0, time=1.7, power=0, reliability=0.99, high_thrust=False,
                 desc="No fuel at all! Sunlight pushes it. Weak far from the Sun."),
}

ENERGY = {
    "nuclear": dict(name="Nuclear (RTG)", mass=3.0, cost=220, output=8.0, storage=60,
                    life_days=99999, solar=False, reliability=0.99,
                    desc="Steady power anywhere for decades. Heavy and expensive."),
    "fuelcell": dict(name="Fuel cells", mass=1.2, cost=60, output=9.0, storage=100,
                     life_days=40, solar=False, reliability=0.90,
                     desc="Strong output, but reactants only last ~40 days."),
    "solar": dict(name="Solar panels", mass=1.0, cost=50, output=10.0, storage=80,
                  life_days=99999, solar=True, reliability=0.95,
                  desc="Free power from sunlight. Output falls with 1/distance^2."),
}

CARGO = {
    "satellite": dict(name="Satellite", mass=2.5, cost=80, science=35, energy=1.0,
                      desc="Orbiter that maps the target from above."),
    "rover": dict(name="Rover", mass=5.0, cost=140, science=50, energy=2.0,
                  desc="Drives across the surface collecting samples."),
    "lander": dict(name="Lander", mass=6.0, cost=110, science=40, energy=1.0,
                   desc="Lands softly on the surface. You fly it down!"),
    "lab": dict(name="Laboratory module", mass=12.0, cost=260, science=80, energy=4.0,
                desc="A full science lab. Heavy and power hungry."),
    "telescope": dict(name="Space telescope", mass=7.0, cost=200, science=65, energy=3.0,
                      desc="Precision optics for deep observations."),
}



def set_multi_cargo(keys):
    """Design Mission: the station's multi-payload bay carrying one payload per stop."""
    keys = [k for k in keys if k in CARGO and k != "multi"]
    if not keys:
        CARGO.pop("multi", None)
        return
    CARGO["multi"] = dict(
        name="Multi-payload bay", mass=sum(CARGO[k]["mass"] for k in keys),
        cost=sum(CARGO[k]["cost"] for k in keys), science=sum(CARGO[k]["science"] for k in keys) / len(keys),
        energy=sum(CARGO[k]["energy"] for k in keys) * 0.3, contents=list(keys),
        desc="Station only: " + ", ".join(CARGO[k]["name"].lower() for k in keys) + " (one per stop).")


# Build steps in order. Each step lists the design keys it fills.
STEPS = [
    ("lv", "LAUNCH VEHICLE", ["lv_size", "material"]),
    ("ship", "SPACECRAFT", ["ship"]),
    ("shield", "HEAT SHIELD", ["shield"]),
    ("engines", "PROPULSION", ["booster", "engine"]),
    ("energy", "POWER", ["energy"]),
    ("cargo", "CARGO", ["cargo"]),
]

TABLES = {
    "lv_size": LV_SIZES, "material": MATERIALS, "ship": SHIPS, "shield": SHIELDS,
    "booster": BOOSTERS, "engine": ENGINES, "energy": ENERGY, "cargo": CARGO,
}

DESIGN_KEYS = ["lv_size", "material", "ship", "shield", "booster", "engine", "energy", "cargo"]


def component_cost(key, choice, design):
    """Cost of one component in the context of the current design."""
    if choice is None:
        return 0.0
    d = TABLES[key][choice]
    if key == "lv_size":
        mat = MATERIALS[design.get("material") or "aluminium"]
        return d["cost"] * mat["cost"]
    if key == "material":
        return 0.0  # material cost is folded into the launch vehicle price
    if key == "booster":
        size = LV_SIZES[design.get("lv_size") or "M"]
        return size["engine_cost"] * d["cost"]
    if key == "shield":
        ship = SHIPS[design.get("ship") or "shuttle"]
        return d["cost"] * ship["area"]
    return float(d["cost"])


class Design:
    """The player's spacecraft design: one choice per design key."""

    def __init__(self, data=None):
        self.c = {k: None for k in DESIGN_KEYS}
        if data:
            self.c.update(data)

    def get(self, k, default=None):
        v = self.c.get(k)
        return default if v is None else v

    def __getitem__(self, k):
        return self.c[k]

    def __setitem__(self, k, v):
        self.c[k] = v

    def comp(self, k):
        v = self.c.get(k)
        return TABLES[k][v] if v else None

    def complete(self):
        return all(self.c[k] for k in DESIGN_KEYS)

    def total_cost(self):
        return sum(component_cost(k, self.c[k], self.c) for k in DESIGN_KEYS)

    def cost_with(self, key, choice):
        trial = dict(self.c)
        trial[key] = choice
        return sum(component_cost(k, trial[k], trial) for k in DESIGN_KEYS)

    def copy(self):
        return Design(dict(self.c))

    def to_dict(self):
        return dict(self.c)
