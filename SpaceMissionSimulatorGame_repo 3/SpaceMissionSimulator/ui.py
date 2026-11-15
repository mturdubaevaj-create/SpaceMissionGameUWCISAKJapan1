"""Reusable pixel-art UI widgets: text, panels, buttons, sliders, text input,
dialogue boxes and Minecraft-style resource bars."""
import math

import pygame

from settings import *

_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = pygame.font.Font(None, size)
    return _fonts[size]


def render(txt, size=16, color=WHITE, scale=1):
    s = font(size).render(str(txt), False, color)
    if scale != 1:
        s = pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))
    return s


def text(surf, txt, pos, color=WHITE, size=16, center=False, right=False, shadow=True, scale=1):
    img = render(txt, size, color, scale)
    x, y = pos
    if center:
        x -= img.get_width() // 2
    elif right:
        x -= img.get_width()
    if shadow:
        sh = render(txt, size, (0, 0, 0), scale)
        surf.blit(sh, (x + scale, y + scale))
    surf.blit(img, (x, y))
    return img.get_width()


def wrap(txt, size, width):
    lines = []
    for para in str(txt).split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            t = (line + " " + w).strip()
            if font(size).size(t)[0] <= width:
                line = t
            else:
                if line:
                    lines.append(line)
                line = w
        lines.append(line)
    return lines


def text_block(surf, txt, rect, color=WHITE, size=16, spacing=0):
    x, y, w, h = rect
    lh = font(size).get_linesize() + spacing
    for line in wrap(txt, size, w):
        if y + lh > rect[1] + h + 2:
            break
        text(surf, line, (x, y), color, size)
        y += lh
    return y


def panel(surf, rect, fill=NAVY, border=LIGHT, border2=None, alpha=None):
    """Chunky retro panel with clipped corners and a 2-tone border."""
    r = pygame.Rect(rect)
    if alpha is not None:
        tmp = pygame.Surface(r.size, pygame.SRCALPHA)
        tmp.fill((*fill, alpha))
        surf.blit(tmp, r.topleft)
    else:
        pygame.draw.rect(surf, fill, r.inflate(-2, -2))
    b2 = border2 or tuple(max(0, c - 80) for c in border)
    pygame.draw.line(surf, border, (r.left + 1, r.top), (r.right - 2, r.top))
    pygame.draw.line(surf, border, (r.left, r.top + 1), (r.left, r.bottom - 2))
    pygame.draw.line(surf, b2, (r.left + 1, r.bottom - 1), (r.right - 2, r.bottom - 1))
    pygame.draw.line(surf, b2, (r.right - 1, r.top + 1), (r.right - 1, r.bottom - 2))


class Button:
    def __init__(self, rect, label, action=None, color=BLUE, text_color=WHITE, size=16,
                 enabled=True, tooltip=None, sound="click", key=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.color = color
        self.text_color = text_color
        self.size = size
        self.enabled = enabled
        self.tooltip = tooltip
        self.sound = sound
        self.hover = False
        self.selected = False
        self.key = key
        self.flash = 0.0

    def handle(self, e, audio=None):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            return self.press(audio)
        if self.key and e.type == pygame.KEYDOWN and e.key == self.key:
            return self.press(audio)
        return False

    def press(self, audio=None):
        if not self.enabled:
            if audio:
                audio.play("deny")
            return True
        if audio and self.sound:
            audio.play(self.sound)
        self.flash = 0.15
        if self.action:
            self.action()
        return True

    def draw(self, surf, dt=0.0):
        self.flash = max(0.0, self.flash - dt)
        base = self.color if self.enabled else (70, 70, 84)
        if self.selected:
            base = tuple(min(255, c + 50) for c in base)
        if self.hover and self.enabled:
            base = tuple(min(255, c + 30) for c in base)
        r = self.rect.copy()
        if self.flash > 0:
            r.move_ip(0, 1)
        # drop shadow
        pygame.draw.rect(surf, (0, 0, 0), r.move(0, 2))
        pygame.draw.rect(surf, base, r)
        hi = tuple(min(255, c + 60) for c in base)
        lo = tuple(max(0, c - 60) for c in base)
        pygame.draw.line(surf, hi, r.topleft, (r.right - 1, r.top))
        pygame.draw.line(surf, hi, r.topleft, (r.left, r.bottom - 1))
        pygame.draw.line(surf, lo, (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
        pygame.draw.line(surf, lo, (r.right - 1, r.top), (r.right - 1, r.bottom - 1))
        if self.selected:
            pygame.draw.rect(surf, YELLOW, r.inflate(2, 2), 1)
        col = self.text_color if self.enabled else (150, 150, 160)
        img = render(self.label, self.size, col)
        surf.blit(img, (r.centerx - img.get_width() // 2, r.centery - img.get_height() // 2 + 1))


def draw_tooltip(surf, txt, pos, size=14):
    if not txt:
        return
    lines = wrap(txt, size, 160)
    lh = font(size).get_linesize()
    w = max(font(size).size(l)[0] for l in lines) + 8
    h = lh * len(lines) + 6
    x = min(pos[0] + 8, W - w - 2)
    y = min(pos[1] + 10, H - h - 2)
    panel(surf, (x, y, w, h), fill=(20, 18, 40), border=YELLOW)
    for i, l in enumerate(lines):
        text(surf, l, (x + 4, y + 3 + i * lh), WHITE, size, shadow=False)


class Slider:
    def __init__(self, rect, value, on_change, label=""):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.on_change = on_change
        self.label = label
        self.drag = False

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.inflate(0, 10).collidepoint(e.pos):
            self.drag = True
            self._set(e.pos[0])
            return True
        if e.type == pygame.MOUSEBUTTONUP:
            self.drag = False
        if e.type == pygame.MOUSEMOTION and self.drag:
            self._set(e.pos[0])
        return False

    def _set(self, x):
        v = max(0.0, min(1.0, (x - self.rect.x) / self.rect.w))
        self.value = round(v * 20) / 20
        self.on_change(self.value)

    def draw(self, surf):
        r = self.rect
        pygame.draw.rect(surf, (0, 0, 0), r.move(0, 1))
        pygame.draw.rect(surf, DARK, r)
        fill = int(r.w * self.value)
        for i in range(0, fill, 4):
            pygame.draw.rect(surf, YELLOW, (r.x + i, r.y + 1, 3, r.h - 2))
        kx = r.x + fill
        pygame.draw.rect(surf, WHITE, (kx - 2, r.y - 3, 5, r.h + 6))
        text(surf, self.label, (r.x, r.y - 14), YELLOW, 16)
        text(surf, "%d%%" % int(self.value * 100), (r.right + 8, r.y - 3), YELLOW, 16)


class TextInput:
    def __init__(self, rect, value="", max_len=14):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.max_len = max_len
        self.t = 0.0

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
                return True
            if e.unicode and e.unicode.isprintable() and len(self.value) < self.max_len \
                    and e.key not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                self.value += e.unicode
                return True
        return False

    def draw(self, surf, dt):
        self.t += dt
        panel(surf, self.rect, fill=BLACK, border=YELLOW)
        w = text(surf, self.value, (self.rect.x + 6, self.rect.y + 6), YELLOW, 24)
        if int(self.t * 2) % 2 == 0:
            pygame.draw.rect(surf, YELLOW, (self.rect.x + 8 + w, self.rect.y + 6, 6, 14))


class DialogueBox:
    """Typewriter dialogue box with a portrait. Feed it messages with say()."""

    def __init__(self, rect, portrait=None, name="", audio=None, color=NAVY, border=CYAN):
        self.rect = pygame.Rect(rect)
        self.portrait = portrait
        self.name = name
        self.audio = audio
        self.queue = []
        self.current = None
        self.shown = 0.0
        self.color = color
        self.border = border
        self.t = 0.0
        self.on_done = None

    @property
    def active(self):
        return self.current is not None

    def say(self, lines, on_done=None):
        if isinstance(lines, str):
            lines = [lines]
        self.queue.extend(lines)
        if on_done:
            self.on_done = on_done
        if self.current is None:
            self._next()

    def clear(self):
        self.queue = []
        self.current = None

    def _next(self):
        if self.queue:
            self.current = self.queue.pop(0)
            self.shown = 0.0
        else:
            self.current = None
            if self.on_done:
                cb, self.on_done = self.on_done, None
                cb()

    def handle(self, e):
        """Returns True if the event was consumed."""
        if not self.active:
            return False
        adv = (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos)) or \
              (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN))
        if adv:
            if self.shown < len(self.current):
                self.shown = len(self.current)
            else:
                self._next()
            return True
        return False

    def update(self, dt):
        self.t += dt
        if self.active and self.shown < len(self.current):
            before = int(self.shown)
            self.shown = min(len(self.current), self.shown + dt * 60)
            if self.audio and int(self.shown) != before and int(self.shown) % 3 == 0:
                self.audio.play("type")

    def draw(self, surf):
        if not self.active:
            return
        r = self.rect
        panel(surf, r, fill=self.color, border=self.border)
        tx = r.x + 6
        if self.portrait:
            p = self.portrait
            pygame.draw.rect(surf, BLACK, (r.x + 4, r.y + 4, p.get_width() + 4, p.get_height() + 4))
            surf.blit(p, (r.x + 6, r.y + 6))
            tx = r.x + p.get_width() + 14
            text(surf, self.name, (r.x + 4, r.y + p.get_height() + 10), YELLOW, 14)
        visible = self.current[:int(self.shown)]
        text_block(surf, visible, (tx, r.y + 5, r.right - tx - 6, r.h - 14), WHITE, 16)
        if self.shown >= len(self.current) and int(self.t * 3) % 2 == 0:
            more = "v" if self.queue else "OK"
            text(surf, more, (r.right - 16, r.bottom - 13), YELLOW, 14)


ICON_GRIDS = {
    "energy": ["..##.", ".##..", "####.", "..##.", ".##..", "##..."],
    "food": [".##..", "####.", "#####", "#####", ".###.", "..#.."],
    "fuel": ["..#..", ".###.", ".###.", "#####", "#####", ".###."],
    "shield": ["#####", "#####", "#####", ".###.", ".###.", "..#.."],
    "integrity": ["#.#.#", "#####", "#...#", "#...#", "#####", "#.#.#"],
    "life": [".#.#.", "#####", "#####", ".###.", "..#..", "....."],
    "crew": [".###.", ".###.", "..#..", "#####", "..#..", ".#.#."],
}


def icon(kind, color, empty=False):
    g = ICON_GRIDS[kind]
    s = pygame.Surface((5, 6), pygame.SRCALPHA)
    for y, row in enumerate(g):
        for x, ch in enumerate(row):
            if ch == "#":
                s.set_at((x, y), (50, 50, 64) if empty else color)
    return s


def resource_bar(surf, x, y, kind, frac, label, critical_t=0.0, value_txt=None, cells=10):
    """Minecraft-hunger-bar style: a row of icons, each can be full/half/empty."""
    col = RESOURCE_COLORS[kind]
    frac = max(0.0, min(1.0, frac))
    crit = frac < 0.2
    shake = 1 if crit and int(critical_t * 8) % 2 == 0 else 0
    text(surf, label, (x, y), col if not crit else RED, 14)
    for i in range(cells):
        ix = x + 46 + i * 7
        iy = y + 2 + (shake if i % 2 else 0)
        surf.blit(icon(kind, col, True), (ix, iy))
        fill = frac * cells - i
        if fill >= 1:
            surf.blit(icon(kind, col), (ix, iy))
        elif fill > 0:
            ic = icon(kind, col)
            surf.blit(ic, (ix, iy), (0, 0, 3, 6))
    t = value_txt if value_txt is not None else "%d%%" % int(frac * 100)
    text(surf, t, (x + 46 + cells * 7 + 3, y), RED if crit else WHITE, 14)
