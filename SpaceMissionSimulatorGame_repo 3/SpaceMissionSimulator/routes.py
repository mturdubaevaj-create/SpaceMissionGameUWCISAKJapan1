"""Trajectory options. Every mission offers two routes from Earth to the target.

SAFE   - long looping path around the danger zones: fewer random events, but the
         trip takes longer (more food, more power, more turns) and needs more
         delta-v, so you need extra fuel or careful PRECISE burns.
DIRECT - short and fast: less fuel, food and power, but straight through the
         asteroid zones and solar activity, so far more dangerous events.

The build screen checks designs against the level's normal values; the chosen
route then scales them. Tweak the numbers here to rebalance.
"""
import copy

HAZARDS = ("asteroid", "micrometeorite", "flare")

ROUTES = {
    "safe": dict(
        name="SAFE ROUTE", num=1,
        dv=1.15,        # x delta-v needed for the transfer
        days=1.5,       # x trip length (food)
        turns=2,        # + extra turns
        events=0.5,     # x chance of a random event each turn
        event_add=0.0,
        hazards=0.35,   # x weight of asteroid / micrometeorite / flare events
        power=1.05,     # x power used each turn
        desc="A long, looping path that steers around asteroid zones and the worst solar activity.",
    ),
    "direct": dict(
        name="DIRECT ROUTE", num=2,
        dv=0.92, days=0.75, turns=0, events=1.0, event_add=0.2, hazards=1.8, power=0.85,
        desc="The fastest, most direct path - straight through the danger zones.",
    ),
}
ORDER = ["safe", "direct"]


def apply_route(level, route_id):
    """Copy of `level` with its game values changed for the chosen route."""
    r = ROUTES[route_id]
    lv = copy.deepcopy(level)
    g = lv["game"]
    g["transfer_dv"] *= r["dv"]
    g["days"] *= r["days"]
    g["turns"] += r["turns"]
    g["event_chance"] = min(0.95, g["event_chance"] * r["events"] + r["event_add"])
    bias = dict(g["event_bias"])
    for k in HAZARDS:
        bias[k] = bias.get(k, 1.0) * r["hazards"]
    g["event_bias"] = bias
    lv["route"] = route_id
    return lv
