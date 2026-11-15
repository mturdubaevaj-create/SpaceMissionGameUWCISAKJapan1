"""Science experiments and mission scoring."""
import random

from spacecraft import CARGO

DIMINISH = [1.0, 0.6, 0.3, 0.15, 0.08, 0.04]

# Add new experiments here. `cost` is taken from resources; `needs` gates it.
EXPERIMENTS = [
    dict(id="engine", name="Engine plume analysis", base=14, cost={"fuel": 1.0},
         desc="Measure exhaust composition and engine efficiency. Uses a little fuel."),
    dict(id="exterior", name="EVA: space environment", base=20, cost={"energy": 6},
         desc="Spacewalk to sample radiation, dust and plasma. Uses energy."),
    dict(id="interior", name="Microgravity biology", base=10, cost={},
         desc="Grow plants and crystals inside the cabin. Free but modest."),
    dict(id="cargo", name="Cargo instrument test", base=16, cost={"energy": 3},
         desc="Calibrate your payload's instruments. Better cargo = more data."),
    dict(id="astronaut", name="Astronaut health study", base=12, cost={"food": 0.5},
         desc="Track bone density, sleep and muscles. Uses some food."),
    dict(id="encounter", name="Study the visitor", base=35, cost={}, needs="encounter",
         desc="Only after meeting a pirate or astronaut. Very valuable!"),
]
EXP_BY_ID = {e["id"]: e for e in EXPERIMENTS}

# Science challenge tiers. The more science an experiment is worth, the harder the
# quiz / mini-game. PAYOUT[tier][correct answers out of 3] = fraction of the stake won.
# -1 means the data is corrupted and the stake is LOST from your total.
TIERS = [  # (id, label, highest stake in this tier)
    ("easy", "EASY", 7),
    ("medium", "MEDIUM", 15),
    ("hard", "HARD", 10 ** 9),
]
PAYOUT = {
    "easy": [-1.0, 0.0, 0.75, 1.0],
    "medium": [-1.0, 0.0, 0.5, 1.0],
    "hard": [-1.0, 0.0, 0.25, 1.0],
}
TIER_COLORS = {"easy": (84, 204, 94), "medium": (255, 214, 64), "hard": (222, 52, 52)}


def tier_for(stake):
    for tid, label, top in TIERS:
        if round(stake) <= top:
            return tid
    return "hard"


def tier_label(tid):
    return {t[0]: t[1] for t in TIERS}[tid]


def payout(tier, correct):
    return PAYOUT[tier][max(0, min(3, correct))]


def payout_text(tier, stake):
    """e.g. '3/3: +14   2/3: +7   1/3: 0   0/3: LOSE 14'"""
    parts = []
    for c in (3, 2, 1, 0):
        f = payout(tier, c)
        if f < 0:
            parts.append("0/3: LOSE %d" % round(stake))
        else:
            parts.append("%d/3: +%d" % (c, round(stake * f)))
    return "   ".join(parts)


def experiment_value(ms, exp_id, preview=False):
    e = EXP_BY_ID[exp_id]
    n = ms.exp_counts.get(exp_id, 0)
    mult = DIMINISH[min(n, len(DIMINISH) - 1)]
    base = e["base"]
    if exp_id == "cargo":
        base *= CARGO[ms.design["cargo"]]["science"] / 50.0
    if exp_id == "exterior":
        base *= 1.0 + 0.5 * ms.progress()  # more interesting closer to the target
    v = base * mult * ms.level["game"]["science_mult"]
    if ms.power_mode == "eco":
        v *= 0.5
    if ms.rations:
        v *= 0.85
    v *= getattr(ms, "turn_sci_mult", 1.0)
    return max(1, round(v)), mult


def compute_score(ms):
    """Returns (rows, total, passed, reasons). rows = [(label, value_text, points)]"""
    g = ms.level["game"]
    rows = []
    alive = ms.failed is None
    sci = ms.science
    rows.append(("Science collected", "%d pts" % sci, int(sci * 10)))
    rows.append(("Astronaut survived", "YES" if alive else "NO", 1000 if alive else 0))
    rows.append(("Objective complete", "YES" if ms.objective_done else "NO", 1000 if ms.objective_done else 0))
    res_avg = (ms.pct("energy") + ms.pct("food") + ms.pct("fuel")) / 3.0
    rows.append(("Resources remaining", "%d%%" % res_avg, int(res_avg * 4)))
    rows.append(("Spacecraft condition", "%d%%" % ms.integrity, int(ms.integrity * 4)))
    rows.append(("Crew health", "%d%%" % ms.crew, int(ms.crew * 3)))
    rows.append(("Experiments run", str(ms.experiments_run), ms.experiments_run * 40))
    budget_left = g["budget"] - ms.design.total_cost()
    rows.append(("Budget saved", "$%dM" % budget_left, int(budget_left)))
    total = sum(r[2] for r in rows)
    reasons = []
    if not alive:
        reasons.append(ms.failed)
    if not ms.objective_done:
        reasons.append("Mission objective not completed")
    if sci < g["science_needed"]:
        reasons.append("Not enough science (%d / %d needed)" % (sci, g["science_needed"]))
    return rows, total, not reasons, reasons
