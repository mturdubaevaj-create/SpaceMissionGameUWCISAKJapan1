"""Global settings, palette and paths for Space Mission Simulator."""
import os

# Internal (logical) resolution. The window is scaled up with nearest-neighbour
# filtering (pygame.SCALED) so everything stays crisp pixel art.
W, H = 480, 270
FPS = 60
TITLE = "Space Mission Simulator - by UWC ISAK-1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
SOUND_DIR = os.path.join(ASSET_DIR, "sounds")
BUNDLED_SOUND_DIR = os.path.join(BASE_DIR, "sounds")   # ready-made .ogg files (used first, works in browsers)
IMAGE_DIR = os.path.join(BASE_DIR, "images")   # your own graphics (PNG) go here
SAVE_FILE = os.path.join(BASE_DIR, "save_data.json")

# ---- Limited retro palette -------------------------------------------------
BLACK = (8, 8, 20)
SPACE = (12, 10, 32)
NAVY = (22, 26, 58)
DARK = (36, 34, 74)
PURPLE = (84, 52, 126)
GREY = (112, 112, 134)
LIGHT = (190, 190, 212)
WHITE = (245, 245, 250)
YELLOW = (255, 214, 64)
GOLD = (220, 170, 50)
ORANGE = (250, 140, 40)
RED = (222, 52, 52)
DARKRED = (128, 22, 32)
GREEN = (84, 204, 94)
DARKGREEN = (30, 112, 62)
CYAN = (84, 204, 232)
BLUE = (52, 104, 212)
BROWN = (134, 92, 60)
PINK = (240, 120, 170)

RESOURCE_COLORS = {
    "energy": YELLOW,
    "food": GREEN,
    "fuel": ORANGE,
    "shield": CYAN,
    "integrity": LIGHT,
    "life": RED,
    "crew": PINK,
}
