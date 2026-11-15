"""Real NASA data used in the game.

* Solar flares: the solar flare event is based on a REAL X-class flare. When the
  computer is online, the game asks NASA's DONKI space-weather database for recent
  flares (in the background, so it never slows the game down) and caches them in
  assets/nasa_flares.json. Offline, it uses the built-in list below.
* Real missions: each destination is compared with a real mission in the report.
* Sources: everything shown on the ABOUT & SOURCES screen.
"""
import json
import os
import random
import threading

from settings import ASSET_DIR

DONKI_URL = ("https://api.nasa.gov/DONKI/FLR?startDate={start}&endDate={end}&api_key=DEMO_KEY")
CACHE_FILE = os.path.join(ASSET_DIR, "nasa_flares.json")

# Built-in fallback: strong solar flares of Solar Cycle 25 (dates in UTC, NOAA active region).
BUILTIN_FLARES = [
    dict(date="2024-10-03", cls="X9.0", region="13842"),
    dict(date="2024-05-14", cls="X8.7", region="13664"),
    dict(date="2024-10-01", cls="X7.1", region="13842"),
    dict(date="2024-02-22", cls="X6.3", region="13590"),
    dict(date="2024-05-11", cls="X5.8", region="13664"),
    dict(date="2023-12-31", cls="X5.0", region="13536"),
    dict(date="2023-12-14", cls="X2.8", region="13514"),
]

_flares = list(BUILTIN_FLARES)
_source = "built-in list (NASA DONKI / NOAA records)"


def _load_cache():
    global _flares, _source
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
        if data.get("flares"):
            _flares = data["flares"]
            _source = "NASA DONKI (downloaded %s)" % data.get("fetched", "earlier")
    except (OSError, ValueError):
        pass


def _fetch():
    """Background download of X-class flares from NASA DONKI. Fails silently when offline."""
    global _flares, _source
    try:
        import datetime
        import urllib.request
        end = datetime.date.today()
        start = end - datetime.timedelta(days=3 * 365)
        url = DONKI_URL.format(start=start.isoformat(), end=end.isoformat())
        with urllib.request.urlopen(url, timeout=6) as r:
            raw = json.loads(r.read().decode("utf-8"))
        out = []
        for f in raw:
            cls = (f.get("classType") or "").strip()
            if cls.startswith("X"):
                out.append(dict(date=(f.get("peakTime") or f.get("beginTime") or "")[:10], cls=cls,
                                region=str(f.get("activeRegionNum") or "?")))
        if out:
            out.sort(key=lambda x: x["date"], reverse=True)
            _flares = out[:40]
            _source = "NASA DONKI (live, %s)" % end.isoformat()
            os.makedirs(ASSET_DIR, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump({"fetched": end.isoformat(), "flares": _flares}, f, indent=1)
    except Exception:   # offline, blocked, rate-limited, browser build... keep the fallback
        pass


def start():
    """Call once at start-up."""
    _load_cache()
    import sys
    if sys.platform == "emscripten":   # web build: no threads or raw sockets, use the built-in list
        return
    try:
        threading.Thread(target=_fetch, daemon=True).start()
    except RuntimeError:
        pass


def flare_class_strength(cls):
    """'X9.0' -> 9.0 (M-class flares count as tenths)."""
    try:
        v = float(cls[1:])
    except ValueError:
        v = 1.0
    return v if cls.startswith("X") else v / 10.0


def random_flare():
    """A real flare and a damage multiplier (bigger flare = more radiation)."""
    f = random.choice(_flares)
    mult = 0.85 + 0.045 * min(10.0, flare_class_strength(f["cls"]))
    return f, mult


def flare_source():
    return _source


# Real missions to compare with the player's trip (shown in the mission report).
REAL_MISSIONS = {
    "moon": "Apollo 11 (1969): launch to lunar orbit in about 3 days; landed on day 4.",
    "mars": "NASA's Perseverance rover (2020-21): 203 days from launch to landing.",
    "venus": "NASA's Magellan (1989-90): about 15 months to reach Venus orbit.",
    "jupiter": "NASA's Juno (2011-16): almost 5 years, using an Earth gravity assist.",
    "saturn": "NASA/ESA Cassini (1997-2004): nearly 7 years, with 4 gravity assists.",
    "sun": "NASA's Parker Solar Probe: first close pass 3 months after launch (2018); "
           "in 2024 it flew 6.1 million km from the Sun's surface.",
    "asteroid": "NASA's OSIRIS-REx: reached Bennu after 2 years (2018) and returned 121.6 g "
                "of Bennu to Earth in 2023.",
    "blackhole": "No spacecraft has ever visited a black hole. The nearest known, Gaia BH1, is about "
                 "1,560 light-years away. The Event Horizon Telescope photographed M87* in 2019.",
}

SOURCES = [
    ("Planet data", "NASA Planetary Fact Sheets (NSSDCA, nssdc.gsfc.nasa.gov)"),
    ("Bennu", "NASA OSIRIS-REx mission and JPL Small-Body Database (ssd.jpl.nasa.gov)"),
    ("Solar flares", "NASA DONKI space weather database (CCMC, ccmc.gsfc.nasa.gov) and NOAA SWPC"),
    ("Missions", "NASA mission pages: Apollo, Perseverance, Magellan, Juno, Cassini, "
                 "Parker Solar Probe, OSIRIS-REx"),
    ("Black holes", "NASA Universe Exploration; Event Horizon Telescope (2019); Gaia BH1 (ESA Gaia, 2022)"),
    ("Physics", "Tsiolkovsky rocket equation, Hohmann transfers, inverse-square law for sunlight"),
    ("Simplified", "Budgets, turn counts, mission delta-v and costs are game values, not real ones"),
]
DISCLAIMER = ("Made for the NASA Space Apps Challenge. Not affiliated with or endorsed by NASA. "
              "NASA data are used under NASA's open data policy.")
