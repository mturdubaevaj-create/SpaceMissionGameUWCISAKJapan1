"""Procedural pixel art: characters, planets, spacecraft, backgrounds.

Everything is drawn in code at low resolution so the game needs no image files.
Characters are defined as text grids (one char = one pixel), which makes them
easy to edit by hand.
"""
import math
import os
import random

import pygame

from settings import *
from spacecraft import MATERIALS, SHIELDS, LV_SIZES

_cache = {}

# ------------------------------------------------------------------ characters
PAL = {
    "k": (20, 18, 30), "h": (96, 60, 36), "s": (236, 190, 150), "w": (245, 245, 250),
    "e": (30, 30, 60), "g": (130, 130, 150), "m": (60, 60, 70), "b": (52, 104, 212),
    "y": (255, 214, 64), "n": (170, 70, 70), "d": (70, 74, 100), "a": (110, 220, 110),
    "A": (54, 150, 70), "p": (160, 90, 200), "P": (90, 40, 110), "r": (222, 52, 52),
    "v": (90, 170, 230), "o": (250, 140, 40), "c": (84, 204, 232),
}

MISSION_CONTROL = [
    "....kkkkkkkk....",
    "...khhhhhhhhk...",
    "..khhhhhhhhhhk..",
    ".gkhsssssssshkg.",
    ".gksswessswesskg",
    ".mksssssssssssk.",
    ".mksssssnsssssk.",
    "..mksssnnnsssk..",
    "...mmkssssssk...",
    "....kkksssskkk..",
    "..kkbbbbbbbbkk..",
    ".kbbbbbybbbbbbk.",
    ".kbbbbbbbbbbbbk.",
    ".kbbkbbbbbbkbbk.",
    ".kssk......kssk.",
    "dddddddddddddddd",
]

FRIENDLY_ALIEN = [
    "......y..y......",
    "......k..k......",
    "....kkaaaaaakk..",
    "...kaaaaaaaaaak.",
    "..kaawwwaawwwaak",
    "..kaaweeaaweeaak",
    "..kaaaaaaaaaaaak",
    "...kaaaAAAAaaak.",
    "....kaaaaaaaak..",
    ".....kkaaaakk...",
    "....kAAAAAAAAk..",
    "...kaAAAAAAAAak.",
    "...kaAAAAAAAAak.",
    "....kAAAAAAAAk..",
    "....kAAk..kAAk..",
    "....kkkk..kkkk..",
]

PIRATE = [
    "...kkkkkkkkkk...",
    "..kkkkkwwkkkkk..",
    ".kkkkkkkkkkkkkk.",
    "...kppppppppk...",
    "..kppwwppkkkpk..",
    "..kppwepppkkppk.",
    "..kpppppppppppk.",
    "..kppkkkykkkppk.",
    "...kppppppppk...",
    "....kkPPPPkk....",
    "..kPPPrPPrPPPk..",
    ".kPPPPPPPPPPPPk.",
    ".kpPPPPPPPPPPpk.",
    ".kpkPPPPPPPPkpk.",
    "...kPPPk.kPPPk..",
    "...kkkkk.kkkkk..",
]

STRANDED = [
    ".....kkkkkk.....",
    "....kwwwwwwk....",
    "...kwwwwwwwwk...",
    "...kwvvvvvvwk...",
    "...kwvssssvwk...",
    "...kwvsesesvwk..",
    "...kwvshhsvwk...",
    "...kwwvvvvwwk...",
    "..kkwwwwwwwwkk..",
    ".kwwwgwwwwogwwk.",
    ".kwwwwwkwwwwwwk.",
    ".kwgwwwwwwwwgwk.",
    ".kwkwwwwwwwwkwk.",
    "...kwwwkkwwwk...",
    "...kwwwk.kwwwk..",
    "...kgggk.kgggk..",
]

PLAYER = [
    ".....kkkkkk.....",
    "....kwwwwwwk....",
    "...kwwwwwwwwk...",
    "...kwvvvvvvwk...",
    "...kwvcvvvvwk...",
    "...kwvvcvvvwk...",
    "...kwvvvvvvwk...",
    "...kwwvvvvwwk...",
    "..kkwwwwwwwwkk..",
    ".kwwwbwwwworwwk.",
    ".kwwwwwwwwwwwwk.",
    ".kwgwwwyywwwgwk.",
    ".kwkwwwwwwwwkwk.",
    "...kwwwkkwwwk...",
    "...kwwwk.kwwwk..",
    "...kgggk.kgggk..",
]


def grid_sprite(grid, scale=1, recolor=None):
    key = ("grid", id(grid), scale, str(recolor))
    if key in _cache:
        return _cache[key]
    pal = dict(PAL)
    if recolor:
        pal.update(recolor)
    h, w = len(grid), len(grid[0])
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != "." and ch in pal:
                surf.set_at((x, y), pal[ch])
    if scale != 1:
        surf = pygame.transform.scale(surf, (w * scale, h * scale))
    _cache[key] = surf
    return surf


# ------------------------------------------------------------------ custom graphics
# Extra looks for characters, loaded from the images/ folder. Each scene that shows
# the character picks one at random (see pick_variant). Missing files are skipped.
CHARACTER_VARIANTS = {
    "alien": ["alien_2.png"],
    "pirate": ["pirate_2.png"],
    "stranded": ["stranded_2.png"],
}
# Pictures that fully REPLACE a character's original drawing.
CHARACTER_REPLACE = {
    "mc": "mission_control.png",
}
VARIANT_CHANCE = 0.35   # chance of using a custom look instead of the original


def custom_image(filename, scale=1):
    """Load a PNG from images/, trimmed to its visible pixels and scaled up crisply.
    Returns None if the file is missing or broken."""
    key = ("img", filename, scale)
    if key in _cache:
        return _cache[key]
    surf = None
    path = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(path):
        try:
            img = pygame.image.load(path)
            img = img.convert_alpha() if pygame.display.get_surface() else img
            img = img.subsurface(img.get_bounding_rect()).copy()
            if scale != 1:
                img = pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))
            surf = img
        except (pygame.error, ValueError):
            surf = None
    _cache[key] = surf
    return surf


def character_picture(filename, scale):
    """A character picture sized like the 16x16 pixel characters at this scale.
    Small pixel art is enlarged in whole pixels; big pictures are shrunk to fit and
    sit at the bottom of the square (so they line up with name labels)."""
    key = ("charpic", filename, scale)
    if key in _cache:
        return _cache[key]
    src = custom_image(filename)
    out = None
    if src is not None:
        box = 16 * scale
        if max(src.get_size()) <= 24:
            out = custom_image(filename, scale)
        else:
            img = fit_image(filename, box, int(box * 1.25))
            out = pygame.Surface((box, max(box, img.get_height())), pygame.SRCALPHA)
            out.blit(img, (box // 2 - img.get_width() // 2, out.get_height() - img.get_height()))
    _cache[key] = out
    return out


def pick_variant(name):
    """None = the original drawing, otherwise the filename of a custom look."""
    options = [f for f in CHARACTER_VARIANTS.get(name, []) if custom_image(f) is not None]
    if options and random.random() < VARIANT_CHANCE:
        return random.choice(options)
    return None


def character(name, scale=2, frame=0, variant=None):
    grids = {"mc": MISSION_CONTROL, "alien": FRIENDLY_ALIEN, "pirate": PIRATE,
             "stranded": STRANDED, "player": PLAYER}
    pic = variant or CHARACTER_REPLACE.get(name)
    s = character_picture(pic, scale) if pic else None
    if s is None:
        s = grid_sprite(grids[name], scale)
    if frame % 2 == 1 and name in ("alien", "pirate"):
        # simple 2-frame bob animation
        out = pygame.Surface((s.get_width(), s.get_height()), pygame.SRCALPHA)
        out.blit(s, (0, scale))
        return out
    return s


# ------------------------------------------------------------------ planets
PLANET_COLORS = {
    "moon": [(70, 70, 82), (130, 130, 144), (190, 190, 200), (225, 225, 232)],
    "mars": [(90, 30, 20), (160, 60, 34), (210, 100, 56), (236, 150, 100)],
    "venus": [(130, 90, 40), (200, 150, 80), (232, 196, 120), (250, 226, 170)],
    "jupiter": [(100, 70, 50), (170, 120, 80), (214, 170, 120), (240, 214, 176)],
    "saturn": [(110, 90, 50), (180, 150, 90), (222, 196, 130), (244, 226, 170)],
    "sun": [(220, 90, 20), (250, 150, 30), (255, 210, 60), (255, 246, 170)],
    "asteroid": [(50, 44, 40), (96, 84, 72), (140, 124, 104), (176, 160, 136)],
    "bennu": [(50, 44, 40), (96, 84, 72), (140, 124, 104), (176, 160, 136)],
    "earth": [(16, 40, 110), (34, 80, 180), (60, 130, 220), (120, 190, 240)],
    "blackhole": [(0, 0, 0)] * 4,
}


# Your own planet pictures (in images/). If a file is missing, the original
# drawing is used. "fit" = how wide the picture is drawn, in planet radii.
PLANET_IMAGES = {
    "moon": ("moon.png", 2.0), "mars": ("mars.png", 2.0), "venus": ("venus.png", 2.0),
    "jupiter": ("jupiter.png", 2.0), "saturn": ("saturn.png", 4.0), "sun": ("sun.png", 2.0),
    "earth": ("earth.png", 2.0), "bennu": ("bennu.png", 2.6), "blackhole": ("blackhole.png", 3.6),
}


def fit_image(filename, w, h):
    """Picture from images/ scaled to fit inside w x h (keeps its shape). None if missing.
    Big pictures are smoothly shrunk; small pixel art is enlarged with crisp pixels."""
    key = ("fit", filename, w, h)
    if key in _cache:
        return _cache[key]
    src = custom_image(filename)
    out = None
    if src is not None:
        k = min(w / src.get_width(), h / src.get_height())
        tw, th = max(1, round(src.get_width() * k)), max(1, round(src.get_height() * k))
        if k < 1 and src.get_bitsize() >= 24:
            out = pygame.transform.smoothscale(src, (tw, th))
        else:
            out = pygame.transform.scale(src, (tw, th))
    _cache[key] = out
    return out


def planet(kind, r):
    """Pixel planet of radius r with quantised lighting from the top-left."""
    key = ("planet", kind, r)
    if key in _cache:
        return _cache[key]
    pad = r if kind in ("saturn", "blackhole") else 2
    if kind in PLANET_IMAGES:
        fname, fit = PLANET_IMAGES[kind]
        size = 2 * r + 2 * pad
        glow = max(3, r // 4)
        if kind == "bennu":
            size = int(2.6 * r) + 4
        elif kind == "sun":
            size = 2 * r + 2 * glow + 2
        img = fit_image(fname, max(2, int(fit * r)), max(2, int(fit * r)) if kind != "saturn" else size)
        if img is not None:
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            c = size // 2
            if kind == "sun":  # keep the soft glow behind your Sun
                for gr in range(r + glow, r - 1, -1):
                    a = int(90 * (1 - (gr - r) / glow))
                    pygame.draw.circle(surf, (255, 180, 40, a), (c, c), gr)
            surf.blit(img, (c - img.get_width() // 2, c - img.get_height() // 2))
            _cache[key] = surf
            return surf
    size = 2 * r + 2 * pad
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    cols = PLANET_COLORS[kind]
    rnd = random.Random(hash(kind) & 0xffff)
    lx, ly, lz = -0.55, -0.55, 0.63
    craters = [(rnd.uniform(-0.7, 0.7), rnd.uniform(-0.7, 0.7), rnd.uniform(0.08, 0.22))
               for _ in range(7)]

    if kind == "sun":  # glow
        for gr in range(r + pad, r, -1):
            a = int(90 * (1 - (gr - r) / pad))
            pygame.draw.circle(surf, (255, 180, 40, a), (cx, cy), gr)
    if kind == "blackhole":
        # accretion disk behind
        for i in range(3):
            pygame.draw.ellipse(surf, [(250, 140, 40), (255, 214, 64), (255, 246, 200)][i],
                                (cx - r - pad + 2 + i * 2, cy - r // 3 + i, 2 * (r + pad) - 4 - i * 4,
                                 2 * r // 3 - i * 2), 2)
    for y in range(-r, r + 1):
        for x in range(-r, r + 1):
            d2 = x * x + y * y
            if d2 > r * r:
                continue
            nx, ny = x / r, y / r
            nz = math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
            lum = max(0.0, nx * lx + ny * ly + nz * lz)
            # Bayer-style dithering between shade levels
            dither = ((x & 1) ^ (y & 1)) * 0.12
            level = min(3, int(lum * 3.6 + dither))
            col = cols[level]
            if kind == "jupiter" or kind == "saturn":
                band = int((ny + 1) * 6) % 3
                if band == 1:
                    col = cols[max(0, level - 1)]
                if kind == "jupiter" and 0.25 < ny < 0.45 and 0.1 < nx < 0.45:
                    col = (200, 70, 50)
            elif kind == "venus":
                if int((ny + nx * 0.3 + 1) * 5) % 2 == 0:
                    col = cols[min(3, level + 1)] if level < 3 else col
            elif kind == "mars":
                if ny < -0.82:
                    col = (240, 240, 245)
                elif (int((nx + 2) * 4) + int((ny + 2) * 3)) % 5 == 0 and level > 0:
                    col = cols[level - 1]
            elif kind == "earth":
                land = math.sin(nx * 5 + 1) * math.cos(ny * 4) + math.sin(nx * 9 + ny * 3)
                if land > 0.9:
                    col = [(20, 80, 30), (40, 130, 50), (80, 170, 70), (130, 200, 100)][level]
                if ny < -0.85 or ny > 0.88:
                    col = (240, 240, 250)
            elif kind == "sun":
                if (x * 7 + y * 13) % 11 == 0:
                    col = cols[3]
            elif kind == "blackhole":
                col = (0, 0, 0)
            if kind in ("moon", "asteroid", "bennu", "mars"):
                for (ccx, ccy, cr) in craters:
                    if (nx - ccx) ** 2 + (ny - ccy) ** 2 < cr * cr:
                        col = cols[max(0, level - 1)]
            surf.set_at((cx + x, cy + y), col)
    if kind in ("asteroid", "bennu"):  # make it lumpy by cutting bites out
        for _ in range(5):
            a = rnd.uniform(0, 2 * math.pi)
            pygame.draw.circle(surf, (0, 0, 0, 0), (int(cx + math.cos(a) * r * 1.1),
                                                    int(cy + math.sin(a) * r * 1.1)),
                               int(r * rnd.uniform(0.3, 0.5)))
    if kind == "saturn":
        ring = pygame.Surface((size, size), pygame.SRCALPHA)
        for i, c in enumerate([(200, 180, 130), (240, 220, 170), (170, 150, 110)]):
            pygame.draw.ellipse(ring, c, (cx - r - pad + 1 + i * 2, cy - r // 3 + i,
                                          2 * (r + pad) - 2 - i * 4, 2 * r // 3 - 2 * i), 1)
        # front half of the ring over the planet
        front = ring.subsurface((0, cy, size, size - cy)).copy()
        back = ring.subsurface((0, 0, size, cy)).copy()
        base = pygame.Surface((size, size), pygame.SRCALPHA)
        base.blit(back, (0, 0))
        base.blit(surf, (0, 0))
        base.blit(front, (0, cy))
        surf = base
    if kind == "blackhole":
        # front part of the disk over the hole
        pygame.draw.arc(surf, (255, 214, 64), (cx - r - pad + 2, cy - r // 3, 2 * (r + pad) - 4,
                                               2 * r // 3), math.pi, 2 * math.pi, 2)
        pygame.draw.circle(surf, (255, 200, 120), (cx, cy), r + 1, 1)
    _cache[key] = surf
    return surf


# ------------------------------------------------------------------ backgrounds
class Starfield:
    """Parallax star layers + static decorations. speed>0 scrolls leftwards."""

    def __init__(self, w=W, h=H, seed=1, density=1.0, decor=True):
        rnd = random.Random(seed)
        self.w, self.h = w, h
        self.layers = []
        for depth, n, col in ((0.2, 90, (90, 90, 130)), (0.5, 50, (170, 170, 210)),
                              (1.0, 22, (255, 255, 255))):
            stars = [[rnd.uniform(0, w), rnd.uniform(0, h), rnd.random()] for _ in range(int(n * density))]
            self.layers.append((depth, stars, col))
        self.bg = pygame.Surface((w, h))
        self.bg.fill(SPACE)
        # nebula clouds made of dithered pixels
        for _ in range(3 if decor else 1):
            cx, cy = rnd.uniform(0, w), rnd.uniform(0, h)
            col = rnd.choice([(40, 20, 70), (20, 30, 70), (60, 20, 50)])
            for _ in range(900):
                a = rnd.uniform(0, 2 * math.pi)
                d = abs(rnd.gauss(0, 40))
                x, y = int(cx + math.cos(a) * d * 1.6), int(cy + math.sin(a) * d)
                if 0 <= x < w and 0 <= y < h and (x + y) % 2 == 0:
                    self.bg.set_at((x, y), col)
        self.t = 0.0

    def update(self, dt, speed=0.0):
        self.t += dt
        for depth, stars, _ in self.layers:
            for s in stars:
                s[0] -= speed * depth * dt
                if s[0] < 0:
                    s[0] += self.w
                    s[1] = random.uniform(0, self.h)

    def draw(self, surf, dim=1.0):
        surf.blit(self.bg, (0, 0))
        for depth, stars, col in self.layers:
            c = tuple(int(v * dim) for v in col)
            for x, y, tw in stars:
                if depth == 1.0 and math.sin(self.t * 3 + tw * 10) > 0.6:
                    surf.set_at((int(x), int(y)), (255, 240, 160))
                    continue
                surf.set_at((int(x), int(y)), c)
                if depth == 1.0 and tw > 0.85:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        xx, yy = int(x) + dx, int(y) + dy
                        if 0 <= xx < self.w and 0 <= yy < self.h:
                            surf.set_at((xx, yy), (120, 120, 170))


# ------------------------------------------------------------------ spacecraft
SHIP_BODY = (232, 232, 240)
SHIP_SHADE = (170, 170, 190)


def _bell(s, cx, y, w, col=(110, 110, 125)):
    pygame.draw.polygon(s, col, [(cx - w // 4, y), (cx + w // 4, y), (cx + w // 2, y + 4),
                                 (cx - w // 2, y + 4)])
    pygame.draw.line(s, (60, 60, 70), (cx - w // 2, y + 4), (cx + w // 2, y + 4))


def draw_ship(design, flight=False):
    """Vertical upper spacecraft (nose up). Partial designs are drawn as far as chosen.
    Returns a Surface (transparent)."""
    key = ("ship", tuple(sorted((k, v) for k, v in design.items() if v)), flight)
    if key in _cache:
        return _cache[key]
    W_, H_ = 60, 80
    s = pygame.Surface((W_, H_), pygame.SRCALPHA)
    cx = W_ // 2
    ship = design.get("ship")
    if not ship:
        _cache[key] = s
        return s
    if ship == "shuttle":
        pic = fit_image("shuttle.png", 36, 46)
        if pic is not None:
            # bottom sits at y=69 so it rests on the launch vehicle in the stack
            s.blit(pic, (cx - pic.get_width() // 2, 69 - pic.get_height()))
            _cache[key] = s
            return s
    bottom = 70
    if ship == "shuttle":
        bw, bh = 10, 24
    elif ship == "heavy":
        bw, bh = 14, 34
    elif ship == "station":
        bw, bh = 16, 44
    else:
        bw, bh = 8, 36
    top = bottom - bh
    # engine
    eng = design.get("engine")
    if eng:
        ecol = {"solid": (120, 120, 130), "liquid": (150, 150, 160), "ion": (60, 120, 220),
                "nuclear": (90, 90, 70), "sail": (180, 180, 190)}[eng]
        if eng == "nuclear":
            pygame.draw.rect(s, (60, 60, 50), (cx - 4, bottom, 8, 5))
            for i in range(0, 8, 2):
                s.set_at((cx - 4 + i, bottom + 2), YELLOW)
            _bell(s, cx, bottom + 5, 8, ecol)
        elif eng == "ion":
            pygame.draw.rect(s, (40, 50, 80), (cx - 4, bottom, 8, 4))
            for i in range(3):
                s.set_at((cx - 3 + i * 3, bottom + 3), CYAN)
        elif eng == "sail":
            _bell(s, cx, bottom, 6, ecol)
        else:
            _bell(s, cx, bottom, 10 if eng == "solid" else 8, ecol)
    # heat shield plate
    sh = design.get("shield")
    if sh:
        pygame.draw.rect(s, SHIELDS[sh]["color"], (cx - bw // 2 - 1, bottom - 3, bw + 2, 3))
    # body
    if ship == "shuttle":
        pygame.draw.rect(s, SHIP_BODY, (cx - bw // 2, top, bw, bh))
        pygame.draw.polygon(s, SHIP_BODY, [(cx - bw // 2, top), (cx + bw // 2 - 1, top), (cx, top - 8)])
        pygame.draw.polygon(s, SHIP_SHADE, [(cx - bw // 2, bottom - 3), (cx - bw // 2 - 8, bottom - 3),
                                            (cx - bw // 2, bottom - 14)])
        pygame.draw.polygon(s, SHIP_SHADE, [(cx + bw // 2 - 1, bottom - 3), (cx + bw // 2 + 7, bottom - 3),
                                            (cx + bw // 2 - 1, bottom - 14)])
        pygame.draw.rect(s, (40, 40, 50), (cx - 2, top - 2, 4, 2))
        pygame.draw.line(s, SHIP_SHADE, (cx + bw // 2 - 1, top), (cx + bw // 2 - 1, bottom - 4))
    elif ship == "heavy":
        pygame.draw.rect(s, SHIP_BODY, (cx - bw // 2, top, bw, bh))
        for yy in (top + 8, top + 20):
            pygame.draw.rect(s, (30, 30, 40), (cx - bw // 2, yy, bw, 3))
        for xx in range(cx - bw // 2, cx + bw // 2, 4):
            pygame.draw.rect(s, (30, 30, 40), (xx, bottom - 8, 2, 5))
        pygame.draw.polygon(s, SHIP_BODY, [(cx - bw // 2, top), (cx + bw // 2 - 1, top), (cx, top - 10)])
        pygame.draw.line(s, (30, 30, 40), (cx, top - 10), (cx, top - 15))
        pygame.draw.line(s, SHIP_SHADE, (cx + bw // 2 - 1, top), (cx + bw // 2 - 1, bottom - 4))
    elif ship == "station":  # interplanetary station: wide core, two rings, cargo pods
        pygame.draw.rect(s, SHIP_BODY, (cx - bw // 2, top, bw, bh))
        pygame.draw.line(s, SHIP_SHADE, (cx + bw // 2 - 1, top), (cx + bw // 2 - 1, bottom - 4))
        for yy in (top + 9, top + 27):
            pygame.draw.ellipse(s, SHIP_BODY, (cx - 26, yy, 52, 9), 2)
            for xx in (cx - 26, cx + 22):
                pygame.draw.rect(s, SHIP_SHADE, (xx, yy + 1, 4, 7))
        for i in range(4):   # cargo pods
            pygame.draw.rect(s, GOLD, (cx - bw // 2 + 2 + (i % 2) * 7, top + 15 + (i // 2) * 16, 5, 6))
        pygame.draw.polygon(s, SHIP_BODY, [(cx - bw // 2, top), (cx + bw // 2 - 1, top), (cx, top - 9)])
        pygame.draw.rect(s, (40, 40, 50), (cx - 3, top + 2, 6, 3))
    else:  # long range: spine + ring + modules
        pygame.draw.rect(s, SHIP_SHADE, (cx - 2, top, 4, bh))
        for yy in (top + 2, top + 12, bottom - 10):
            pygame.draw.rect(s, SHIP_BODY, (cx - bw // 2, yy, bw, 7))
            pygame.draw.rect(s, (60, 60, 80), (cx - 1, yy + 2, 2, 2))
        ry = top + bh // 2 - 3
        pygame.draw.ellipse(s, SHIP_BODY, (cx - 22, ry, 44, 8), 2)
        for xx in (cx - 22, cx + 18):
            pygame.draw.rect(s, SHIP_SHADE, (xx, ry + 1, 4, 6))
        pygame.draw.polygon(s, SHIP_BODY, [(cx - bw // 2, top + 2), (cx + bw // 2 - 1, top + 2), (cx, top - 5)])
    # power system
    en = design.get("energy")
    if en:
        my = top + bh // 2 + (6 if ship == "longrange" else 0)
        if en == "solar":
            if flight:
                for side in (-1, 1):
                    x0 = cx + side * (bw // 2 + 1) if side > 0 else cx - bw // 2 - 15
                    pygame.draw.rect(s, (40, 70, 160), (x0, my - 3, 14, 7))
                    for gx in range(x0, x0 + 14, 3):
                        pygame.draw.line(s, (90, 140, 230), (gx, my - 3), (gx, my + 3))
            else:
                for side in (-1, 1):
                    x0 = cx + bw // 2 if side > 0 else cx - bw // 2 - 3
                    pygame.draw.rect(s, (40, 70, 160), (x0, my - 6, 3, 12))
        elif en == "nuclear":
            x0 = cx + bw // 2
            pygame.draw.line(s, (90, 90, 100), (x0, my), (x0 + 5, my))
            pygame.draw.rect(s, (50, 50, 56), (x0 + 5, my - 4, 4, 9))
            for yy in range(my - 4, my + 5, 2):
                pygame.draw.line(s, (90, 90, 100), (x0 + 3, yy), (x0 + 10, yy))
        else:  # fuel cells: white tanks
            for side in (-1, 1):
                x0 = cx + bw // 2 if side > 0 else cx - bw // 2 - 4
                pygame.draw.rect(s, (250, 250, 255), (x0, my - 4, 4, 8))
                s.set_at((x0 + 1, my - 3), (180, 180, 200))
    # cargo on the nose
    cg = design.get("cargo")
    if cg:
        ny = top - (10 if ship == "heavy" else 8 if ship == "shuttle" else 5)
        if cg == "satellite":
            pygame.draw.rect(s, GOLD, (cx - 3, ny - 6, 6, 5))
            pygame.draw.arc(s, LIGHT, (cx - 4, ny - 11, 8, 6), 0, math.pi, 1)
        elif cg == "rover":
            pygame.draw.rect(s, (220, 220, 230), (cx - 4, ny - 6, 8, 4))
            for xx in (cx - 4, cx, cx + 3):
                pygame.draw.rect(s, (40, 40, 40), (xx, ny - 2, 2, 2))
        elif cg == "lander":
            pygame.draw.rect(s, GOLD, (cx - 3, ny - 7, 6, 5))
            pygame.draw.line(s, LIGHT, (cx - 3, ny - 2), (cx - 5, ny))
            pygame.draw.line(s, LIGHT, (cx + 2, ny - 2), (cx + 4, ny))
            pygame.draw.rect(s, (40, 40, 60), (cx - 1, ny - 6, 2, 2))
        elif cg == "lab":
            pygame.draw.rect(s, (245, 245, 250), (cx - 3, ny - 10, 6, 9))
            pygame.draw.rect(s, BLUE, (cx - 3, ny - 7, 6, 1))
        else:  # telescope
            pygame.draw.rect(s, (200, 200, 210), (cx - 2, ny - 11, 5, 10))
            pygame.draw.rect(s, GOLD, (cx - 3, ny - 12, 7, 2))
    if eng == "sail":
        if flight:
            pygame.draw.polygon(s, (220, 220, 235), [(cx, 2), (cx + 26, top + 6), (cx, top + 14),
                                                     (cx - 26, top + 6)])
            pygame.draw.line(s, (150, 150, 170), (cx, 2), (cx, top + 14))
            pygame.draw.line(s, (150, 150, 170), (cx - 26, top + 6), (cx + 26, top + 6))
        else:
            pygame.draw.rect(s, (200, 200, 215), (cx - bw // 2 - 4, top + 4, 3, 8))
    _cache[key] = s
    return s


def draw_launch_vehicle(design):
    size = design.get("lv_size")
    if not size:
        return None
    key = ("lv", size, design.get("material"), design.get("booster"))
    if key in _cache:
        return _cache[key]
    d = LV_SIZES[size]
    w, h = d["w"], d["h"]
    mat = MATERIALS[design.get("material") or "aluminium"]
    col = mat["color"] if design.get("material") else (120, 120, 140)
    dark = mat["dark"] if design.get("material") else (80, 80, 100)
    s = pygame.Surface((w + 20, h + 8), pygame.SRCALPHA)
    x0 = 10
    pic = lv_picture(size, h + 6)
    if pic is not None:
        pic = pic.copy()
        pic.fill(col + (255,), special_flags=pygame.BLEND_RGBA_MULT)   # tint by material
        if design.get("booster") == "solid":   # solid boosters still show beside the rocket
            for bx in (s.get_width() // 2 - pic.get_width() // 2 - 6, s.get_width() // 2 + pic.get_width() // 2 + 1):
                pygame.draw.rect(s, (240, 240, 245), (bx, int(h * 0.3), 5, int(h * 0.7)))
                pygame.draw.polygon(s, (240, 240, 245), [(bx, int(h * 0.3)), (bx + 4, int(h * 0.3)),
                                                         (bx + 2, int(h * 0.3) - 4)])
                pygame.draw.rect(s, (60, 60, 70), (bx, h - 1, 5, 3))
        s.blit(pic, (s.get_width() // 2 - pic.get_width() // 2, h + 6 - pic.get_height()))
        _cache[key] = s
        return s
    pygame.draw.rect(s, col, (x0, 0, w, h))
    pygame.draw.rect(s, dark, (x0 + w - 3, 0, 3, h))
    # interstage band + stage separation
    pygame.draw.rect(s, (30, 30, 40), (x0, 0, w, 3))
    pygame.draw.rect(s, (30, 30, 40), (x0, int(h * 0.36), w, 2))
    # flag-ish stripe + text pixels
    pygame.draw.rect(s, RED, (x0 + 2, int(h * 0.5), 3, 6))
    pygame.draw.rect(s, BLUE, (x0 + 2, int(h * 0.5) + 6, 3, 3))
    # fins
    pygame.draw.polygon(s, dark, [(x0, h - 10), (x0 - 5, h), (x0, h)])
    pygame.draw.polygon(s, dark, [(x0 + w, h - 10), (x0 + w + 4, h), (x0 + w, h)])
    b = design.get("booster")
    if b == "solid":
        for bx in (x0 - 7, x0 + w + 2):
            pygame.draw.rect(s, (240, 240, 245), (bx, int(h * 0.3), 5, int(h * 0.7)))
            pygame.draw.polygon(s, (240, 240, 245), [(bx, int(h * 0.3)), (bx + 4, int(h * 0.3)),
                                                     (bx + 2, int(h * 0.3) - 4)])
            pygame.draw.rect(s, (60, 60, 70), (bx, h - 1, 5, 3))
    if b:
        n = 2 if size == "S" else 3
        for i in range(n):
            ex = x0 + 2 + i * (w - 4) // max(1, n - 1) if n > 1 else x0 + w // 2
            _bell(s, ex, h, 6, (90, 90, 100) if b != "ion" else (60, 120, 220))
    _cache[key] = s
    return s


LV_PICTURES = {"L": "launch_vehicle_L.png"}
LV_TRIM_TOP = 0.12   # cut off the nose tip so the spacecraft sits on a flat top


def lv_picture(size, height):
    """Launch vehicle picture for this size (nose tip trimmed), `height` px tall. None if missing."""
    fname = LV_PICTURES.get(size)
    key = ("lvpic", size, height)
    if key in _cache:
        return _cache[key]
    out = None
    src = custom_image(fname) if fname else None
    if src is not None:
        cut = int(src.get_height() * LV_TRIM_TOP)
        body = src.subsurface((0, cut, src.get_width(), src.get_height() - cut)).copy()
        wdt = max(1, round(body.get_width() * height / body.get_height()))
        out = pygame.transform.smoothscale(body, (wdt, height))
    _cache[key] = out
    return out


def draw_stack(design):
    """LV + ship stacked vertically. Returns (surface, ship_offset_y)."""
    lv = draw_launch_vehicle(design)
    ship = draw_ship(design) if design.get("ship") else None
    lvh = lv.get_height() if lv else 0
    total_h = lvh + (66 if ship else 0)
    surf = pygame.Surface((64, max(1, total_h)), pygame.SRCALPHA)
    if ship:
        surf.blit(ship, (2, 0))
    if lv:
        surf.blit(lv, (32 - lv.get_width() // 2, total_h - lvh))
    return surf


def crane(height):
    """Red launch gantry tower."""
    s = pygame.Surface((26, height), pygame.SRCALPHA)
    red, dark = (210, 40, 40), (130, 20, 26)
    pygame.draw.rect(s, red, (2, 0, 3, height))
    pygame.draw.rect(s, red, (12, 0, 3, height))
    for y in range(0, height - 6, 8):
        pygame.draw.line(s, dark, (2, y), (14, y + 8))
        pygame.draw.line(s, dark, (14, y), (2, y + 8))
        pygame.draw.line(s, red, (2, y), (14, y))
    pygame.draw.rect(s, red, (0, 0, 26, 3))  # top boom
    pygame.draw.line(s, (240, 240, 240), (24, 3), (24, 12))
    return s


def explosion(surf, x, y, t):
    """Draw an animated pixel explosion (t from 0 to 1)."""
    rnd = random.Random(int(x) * 31 + int(y))
    for i in range(40):
        a = rnd.uniform(0, 2 * math.pi)
        sp = rnd.uniform(5, 40)
        r = sp * t
        px, py = int(x + math.cos(a) * r), int(y + math.sin(a) * r)
        c = [WHITE, YELLOW, ORANGE, RED, GREY][min(4, int(t * 5 + rnd.random()))]
        size = max(1, int(3 * (1 - t)) + 1)
        pygame.draw.rect(surf, c, (px, py, size, size))
