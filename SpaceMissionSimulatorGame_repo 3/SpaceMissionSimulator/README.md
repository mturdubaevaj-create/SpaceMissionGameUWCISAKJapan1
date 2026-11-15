# SPACE MISSION SIMULATOR
### by UWC ISAK-1 - NASA Space Apps Challenge

A retro pixel-art game where you design a spacecraft, launch it through Earth's atmosphere, survive deep-space random events, collect science, and complete a cargo objective at 8 destinations, ending with the Black Hole.

## How to run
```
pip install pygame
python main.py
```
Python 3.8+ with pygame 2.x. The first launch takes about a second to synthesise the 8-bit music and sound effects into `assets/sounds/`. Progress, settings, player name and learned facts are saved in `save_data.json`.

**Controls:** use the mouse for menus. F11 toggles fullscreen. In the mini-games use the arrow keys / WASD and SPACE. SPACE or ENTER also advances dialogue.

## Game flow
Main menu → name entry → destination map → mission briefing → **build ship** (6 steps) → **choose trajectory** (safe or direct route) → launch pad countdown → atmosphere ascent → **turn-based mission** (random events, ship-system alerts, one science experiment + challenge per turn, ship adjustments) → cargo mini-game → mission report → next destination unlocked. The Black Hole unlocks after all 7 other missions are complete and leads to the ending and credits.

Between screens, Zorp the friendly alien teaches a NASA fact. These facts are the only source for the alien pirate's quiz and the stranded astronaut's true/false statements. You are never tested on something you haven't seen.

## Gameplay systems
- **WHY? button (build screen):** when the design has a problem, WHY? explains what the problem means, shows your numbers, and lists which parts affect it, without saying which part to pick. Every part's tooltip also says what it affects (`advice.py`).
- **Trajectory (`routes.py`, `trajectory.py`):** after building, pick a route. **1. Safe:** fewer random events (half the chance, far fewer asteroids/flares/micrometeorites), but the trip is 1.5x longer, has 2 more turns and needs 15% more delta-v. **2. Direct:** 25% shorter trip, 8% less delta-v and 15% less power per turn, but far more dangerous events. The route cards show fuel, food and power for the ship you built.
- **Precise burns (Adjust Ship):** use 20% less propellant on every engine burn, but each major burn costs 8% energy. The top bar shows *FUEL TO ARRIVE* vs fuel left.
- **Systems alerts (`systems.py`):** most turns (75%) something goes wrong with the ship: solar panels drift off-Sun, the reactor runs hot, fuel cells flood, batteries unbalance, heaters stick on. Every choice costs something (energy, fuel, food, spare parts, or a risk).
- **Science challenges (`sciencegame.py`, `science_questions.py`):** every experiment ends with a quiz or mini-game (sensor calibration, data stream recall), 3 rounds. Value 1-7 = EASY (3/3 100%, 2/3 75%), 8-15 = MEDIUM (2/3 50%), 16+ = HARD (2/3 25%). 1/3 gives nothing and 0/3 **loses** the stake. Tune in `science.PAYOUT`.

- **Crew health:** radiation and injuries lower the CREW bar; at 0 the mission fails.
- **Solar flare (`events.py`):** walk the astronaut (arrows/WASD) to the best-shielded room before the flare hits.
  Pantry/water or the storm shelter (long-range ships) protect best, the cockpit worst; caught in the corridor = fatal.
  Each flare is based on a REAL X-class flare from NASA's DONKI database (`nasa_data.py`).
- **Repairs:** equipment failures are fixed with a wiring puzzle (power / life support), a star-tracker
  alignment (navigation) or a valve sequence (fuel).
- **Docking:** a space station sometimes appears. Dock gently for +20% fuel, +10% energy, +15% food; a rough
  dock damages the hull, a crash ends the mission; flying past is free.
- **Black Hole:** on the first visit choose ENTER (the fall-in ending) or TURN BACK (alarms as power and food
  run out). Both roll the credits; click afterwards to return to the map. Later visits are science missions.
- **Fact Book and About & Sources** screens in the main menu; mission reports compare your trip with a real
  NASA mission.

## Design Mission (`design.py`)
Unlocks after completing Saturn. Launch from Earth, the Moon, Mars or Bennu (`physics.LAUNCH_SITES`), visit
up to 5 unlocked destinations in any order, and set your own budget (a recommended budget is calculated by
searching for the cheapest design that can do the whole trip). The Interplanetary Station (design missions
only) carries one payload per stop; other ships deploy their single payload at the first stop that can use it
and do science fly-bys elsewhere. Choose a route before every leg; supplies, hull and crew health carry over.
Leaving Jupiter or Saturn gives a gravity assist. Travel between any two places uses Hohmann-transfer maths,
calibrated to the main game's Earth trips.

## Web version (for judges: play in a browser, nothing to install)
The game loop is async, so it can be packaged with pygbag. On a computer with internet, from the folder
that CONTAINS `SpaceMissionSimulator`:
```
pip install pygbag
python -m pygbag SpaceMissionSimulator
```
then open http://localhost:8000 to test. For upload (e.g. itch.io, "HTML" project), build a zip:
```
python -m pygbag --archive SpaceMissionSimulator
```
and upload `SpaceMissionSimulator/build/web.zip`. Notes: the first load in a browser takes a while (it
synthesises the music), the live NASA flare download is skipped in the browser (the built-in real flare list
is used), and progress is not kept after the browser tab is closed.

## The physics (physics.py)
- **Rocket equation** for each stage: `dv = Isp * g0 * ln(m0 / mf)`. The launch vehicle is modelled as two stages, and the spacecraft is a third.
- **Thrust-to-weight ratio** must be above 1.15 to leave the pad. A low TWR also adds gravity losses.
- Reaching low Earth orbit needs about 9.4 km/s (7.8 km/s orbital speed plus losses). Any surplus from the launch vehicle can do the departure burn, like Saturn V's S-IVB did. The spacecraft must always do its own arrival burn.
- **Max velocity** = 7.8 km/s + the remaining delta-v. It must exceed Earth's escape velocity of 11.2 km/s.
- **Heat rating** = 40% launch-vehicle material + 60% heat shield. It is checked during ascent (needs 45) and at atmospheric entry (Mars, the Sun).
- **Max-Q:** structural strength must survive the aerodynamic stress. Violent, high-TWR rockets need stronger materials.
- **Power:** solar output falls with 1/distance². Fuel cells run out after about 40 days. An RTG works anywhere.
- **Food:** the ship's food storage must cover the trip length. Ion engines and solar sails make trips longer.

The real-world data in the briefings (temperatures, gravity, escape velocities, distances) is real. Budgets, turn counts and mission delta-v values are game simplifications, and each level's briefing says so.

## Balance
`balance_check.py` brute-forces every one of the 32,400 possible designs for every level. It confirms that each mission has viable designs within its budget, and that only a small fraction of affordable designs work. Run it after changing any numbers.

## Your own graphics
Put PNG files in the `images/` folder. Character variants are listed in `art.CHARACTER_VARIANTS`
(e.g. `"alien": ["alien_2.png"]`). Each time the character appears there is a `VARIANT_CHANCE`
(35%) chance it uses one of these instead of the original pixel art. Transparent backgrounds work best;
the image is trimmed to its visible pixels automatically.

Planet pictures are listed in `art.PLANET_IMAGES` (moon, mars, venus, jupiter, saturn, sun, earth,
bennu, blackhole). Cargo pictures used in the mini-games: `lander.png`, `rover.png`, `satellite.png`.
Also: `mission_control.png` (replaces Mission Control, `art.CHARACTER_REPLACE`), `pirate_2.png` and `stranded_2.png`
(occasional pirate / stranded astronaut looks), `shuttle.png` (Shuttle spacecraft), `launch_vehicle_L.png` (Large launch vehicle,
tinted by material, nose tip trimmed by `art.LV_TRIM_TOP`), `atmosphere.png` (ascent screen background;
layer positions are set by `BG_*` in `launch.py`).
Delete or rename any of these files to go back to the original drawing.

## Code structure
| File | Purpose |
|---|---|
| `main.py` | Game loop, scene switching |
| `settings.py` | Resolution, palette, paths |
| `scene.py` | Scene base, Mission Control guide, friendly alien and loading screen |
| `menu.py` | Main menu, settings (volume sliders), player setup |
| `levels.py` | Destination data (real values and game values) |
| `levelselect.py` | Destination map and mission briefing |
| `spacecraft.py` | Component database and the Design class |
| `build.py` | Spacecraft construction interface |
| `physics.py` | Rocket physics and performance analysis |
| `launch.py` | Launch pad countdown and atmospheric ascent |
| `mission.py` | Mission state (resources, burns, turns) and the main mission screen |
| `events.py` | Random events (asteroids, micrometeorite, malfunction, solar flare, pirate, stranded astronaut) |
| `science.py` | Experiments, diminishing returns, scoring |
| `landing.py` | Cargo mini-games (lander, rover, satellite, telescope, lab) |
| `endings.py` | Game over, mission report, black hole finale, credits |
| `facts.py` | NASA fact / question database |
| `ui.py`, `art.py`, `audio.py` | Widgets, procedural pixel art, chiptune synthesiser |
| `advice.py` | Build-screen WHY? explanations |
| `routes.py`, `trajectory.py` | Route data and the trajectory selection screen |
| `systems.py` | Per-turn ship-system alerts |
| `sciencegame.py`, `science_questions.py` | Science challenges and their question bank |
| `design.py` | Design Mission: planner, travel maths, multi-leg flow, report |
| `nasa_data.py` | Real NASA data: solar flares (DONKI), real mission comparisons, sources |
| `extras.py` | Fact Book and About & Sources screens |

## Adding content
- **New planet:** add a dict to `LEVELS` in `levels.py`. Add a colour palette in `art.PLANET_COLORS` if it needs a new icon.
- **New component:** add an entry to the matching table in `spacecraft.py`.
- **New random event:** subclass `EventScene` in `events.py`, register it in `EVENTS`, and give it a weight in `MissionScene.choose_event`.
- **New experiment:** append to `EXPERIMENTS` in `science.py`.
- **New fact/question:** append to `FACTS` in `facts.py` (the first option is the correct answer).
- **New systems alert:** add a dict to `ALERTS` in `systems.py`.
- **New science question:** append to `EASY`, `MEDIUM` or `HARD` in `science_questions.py` (first answer is correct).
- **New cargo mini-game:** subclass `MiniGame` in `landing.py` and register it in `MINIGAMES`.

## Credits
Special thanks to **Leo H and Zhamilia** (Design Team) and **Madalitso, Aron and Luka** (Coding Team).
