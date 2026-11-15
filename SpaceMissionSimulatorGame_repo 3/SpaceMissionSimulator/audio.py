"""8-bit audio: a tiny chiptune synthesizer + music/sfx manager.

All music and sound effects are synthesised in pure Python the first time the
game runs and cached as .wav files in assets/sounds/. Delete that folder to
regenerate them. No external audio files are needed.
"""
import array
import math
import os
import random
import wave

import pygame

from settings import SOUND_DIR, BUNDLED_SOUND_DIR

RATE = 22050
NOTE_INDEX = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7,
              "G#": 8, "A": 9, "A#": 10, "B": 11}


def midi(name):
    """'A4' -> 69,  'C#5' -> 73."""
    n, octave = name[:-1], int(name[-1])
    return 12 * (octave + 1) + NOTE_INDEX[n]


def parse(seq):
    """'E5:2 A5:2 -:1' -> [(76, 2), (81, 2), (None, 1)] (lengths in 16th notes)."""
    out = []
    for tok in seq.split():
        n, l = tok.split(":")
        out.append((None if n == "-" else midi(n), float(l)))
    return out


def _voice(buf, notes, kind, vol, step, gate=0.9):
    pos = 0
    for m, length in notes:
        n = int(length * step)
        if m is not None:
            f = 440.0 * 2 ** ((m - 69) / 12.0)
            inc = f / RATE
            on = int(n * gate)
            rel = max(1, min(on // 3, 900))
            ph = 0.0
            for i in range(min(on, len(buf) - pos)):
                p = ph % 1.0
                if kind == "sq":
                    s = 1.0 if p < 0.5 else -1.0
                elif kind == "sq25":
                    s = 1.0 if p < 0.25 else -1.0
                elif kind == "tri":
                    s = 4.0 * abs(p - 0.5) - 1.0
                else:  # saw
                    s = 2.0 * p - 1.0
                env = 1.0
                if i < 60:
                    env = i / 60.0
                elif i > on - rel:
                    env = (on - i) / rel
                buf[pos + i] += s * vol * env
                ph += inc
        pos += n


def _drums(buf, pattern, step, vol=0.5):
    """pattern string per 16th: k=kick s=snare h=hat .=rest"""
    rnd = random.Random(7)
    for idx, ch in enumerate(pattern):
        start = int(idx * step)
        if ch == "k":
            n = int(0.14 * RATE)
            ph = 0.0
            for i in range(min(n, len(buf) - start)):
                f = 160 - 110 * (i / n)
                ph += f / RATE
                buf[start + i] += math.sin(ph * 2 * math.pi) * vol * (1 - i / n)
        elif ch in "sh":
            n = int((0.12 if ch == "s" else 0.025) * RATE)
            v = vol * (0.7 if ch == "s" else 0.3)
            for i in range(min(n, len(buf) - start)):
                buf[start + i] += (rnd.random() * 2 - 1) * v * (1 - i / n)


def _write(path, buf):
    peak = max(1e-6, max(abs(x) for x in buf))
    scale = 28000 / max(peak, 1.0)
    data = array.array("h", (int(max(-32767, min(32767, x * scale))) for x in buf))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def _song(bpm, bars, voices, drum_pattern=None, drum_vol=0.45):
    step = RATE * 60.0 / bpm / 4.0
    buf = [0.0] * int(bars * 16 * step + RATE * 0.05)
    for notes, kind, vol, gate in voices:
        _voice(buf, notes, kind, vol, step, gate)
    if drum_pattern:
        _drums(buf, drum_pattern * bars, step, drum_vol)
    return buf


def _chord_arp(chords, octave_notes, per_bar=16):
    seq = []
    for c in chords:
        tones = octave_notes[c]
        for i in range(per_bar):
            seq.append((midi(tones[i % len(tones)]), 1))
    return seq


def _bass(chords, roots):
    seq = []
    for c in chords:
        r = midi(roots[c])
        for i in range(8):
            seq.append((r if i % 2 == 0 else r + 12, 2))
    return seq


# ------------------------------------------------------------------ the music
def make_menu_theme():
    chords = ["Am", "F", "C", "G", "Am", "F", "C", "G", "Dm", "F", "G", "E", "Dm", "F", "G", "E"]
    roots = {"Am": "A2", "F": "F2", "C": "C3", "G": "G2", "Dm": "D3", "E": "E2"}
    arp = {"Am": ["A4", "C5", "E5", "A5"], "F": ["F4", "A4", "C5", "F5"],
           "C": ["E4", "G4", "C5", "E5"], "G": ["G4", "B4", "D5", "G5"],
           "Dm": ["D4", "F4", "A4", "D5"], "E": ["E4", "G#4", "B4", "E5"]}
    lead = parse(
        "E5:2 A5:2 -:1 A5:1 G5:2 E5:2 C5:2 D5:2 E5:2 "
        "F5:4 E5:2 C5:2 A4:4 C5:4 "
        "G5:2 E5:2 G5:2 C6:4 B5:2 G5:4 "
        "D5:6 B4:2 D5:4 G5:4 "
        "E5:2 A5:2 -:1 A5:1 G5:2 E5:2 C5:2 D5:2 E5:2 "
        "F5:2 A5:2 C6:4 A5:2 F5:2 E5:4 "
        "E5:2 G5:2 C6:2 E6:2 D6:4 C6:4 "
        "B5:8 -:4 D5:4 "
        "F5:4 A5:4 D6:4 A5:4 "
        "C6:4 A5:2 F5:2 C6:4 F6:4 "
        "D6:2 B5:2 G5:2 B5:2 D6:4 G6:4 "
        "E6:8 D6:2 C6:2 B5:4 "
        "F5:2 F5:2 A5:2 D6:4 C6:2 A5:4 "
        "C6:2 C6:2 A5:2 F5:4 G5:2 A5:4 "
        "B5:4 D6:4 G6:4 F6:4 "
        "G#5:4 B5:4 E6:8")
    return _song(140, 16, [
        (lead, "sq", 0.30, 0.85),
        (_chord_arp(chords, arp), "sq25", 0.10, 0.6),
        (_bass(chords, roots), "tri", 0.38, 0.8),
    ], drum_pattern="k.h.s.h.k.k.s.hh")


def make_mission_theme():
    chords = ["Am", "Em", "F", "G", "Am", "Em", "F", "E"]
    roots = {"Am": "A2", "Em": "E2", "F": "F2", "G": "G2", "E": "E2"}
    arp = {"Am": ["A4", "E5", "C5", "E5"], "Em": ["E4", "B4", "G4", "B4"],
           "F": ["F4", "C5", "A4", "C5"], "G": ["G4", "D5", "B4", "D5"],
           "E": ["E4", "B4", "G#4", "B4"]}
    lead = parse(
        "A5:6 G5:2 E5:8 B4:6 D5:2 E5:8 C5:6 D5:2 E5:4 F5:4 D5:12 B4:4 "
        "A5:6 B5:2 C6:8 B5:6 G5:2 E5:8 F5:4 E5:4 C5:4 A4:4 G#4:12 -:4")
    return _song(96, 8, [
        (lead, "tri", 0.34, 0.95),
        (_chord_arp(chords, arp), "sq25", 0.08, 0.5),
        (_bass(chords, roots), "tri", 0.32, 0.9),
    ], drum_pattern="k.......s.......", drum_vol=0.3)


def make_ending_theme():
    chords = ["C", "G", "Am", "F", "C", "G", "F", "C"]
    roots = {"C": "C3", "G": "G2", "Am": "A2", "F": "F2"}
    arp = {"C": ["C4", "E4", "G4", "C5"], "G": ["B3", "D4", "G4", "B4"],
           "Am": ["A3", "C4", "E4", "A4"], "F": ["A3", "C4", "F4", "A4"]}
    lead = parse("E5:8 G5:8 D5:8 B4:8 C5:8 E5:8 F5:8 A5:8 "
                 "G5:8 E5:8 D5:8 G5:8 A5:8 F5:8 E5:12 -:4")
    return _song(70, 8, [
        (lead, "tri", 0.36, 0.97),
        (_chord_arp(chords, arp), "tri", 0.12, 0.7),
        (_bass(chords, roots), "tri", 0.3, 0.95),
    ])


# ------------------------------------------------------------------ the sfx
def _tone(f0, f1, dur, kind="sq", vol=0.6):
    n = int(dur * RATE)
    buf = [0.0] * n
    ph = 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * i / n
        ph += f / RATE
        p = ph % 1.0
        s = (1.0 if p < 0.5 else -1.0) if kind == "sq" else 4 * abs(p - 0.5) - 1
        buf[i] = s * vol * (1 - i / n) ** 0.5
    return buf


def _noise(dur, vol=0.6, decay=1.0, rumble=False):
    rnd = random.Random(3)
    n = int(dur * RATE)
    buf = [0.0] * n
    last = 0.0
    for i in range(n):
        x = rnd.random() * 2 - 1
        if rumble:  # crude low-pass for deep rumbles
            last = last * 0.92 + x * 0.08
            x = last * 4
        buf[i] = x * vol * (1 - i / n) ** decay
    return buf


def _concat(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def make_sfx():
    return {
        "click": _tone(900, 600, 0.05),
        "select": _concat(_tone(660, 660, 0.05), _tone(990, 990, 0.07)),
        "back": _tone(500, 300, 0.08),
        "deny": _concat(_tone(200, 180, 0.08), _tone(150, 140, 0.1)),
        "beep": _tone(880, 880, 0.12),
        "go": _tone(1320, 1320, 0.4),
        "launch": _noise(3.5, 0.9, 0.6, rumble=True),
        "explosion": _concat(_noise(0.1, 1.0, 0.2), _noise(1.4, 0.9, 1.5, rumble=True)),
        "alarm": _concat(_tone(900, 600, 0.25), _tone(900, 600, 0.25)),
        "success": _concat(_tone(523, 523, 0.1), _tone(659, 659, 0.1), _tone(784, 784, 0.1),
                           _tone(1047, 1047, 0.3)),
        "fail": _concat(_tone(400, 380, 0.2), _tone(300, 280, 0.2), _tone(200, 120, 0.5)),
        "hit": _concat(_noise(0.15, 0.9, 1.0), _tone(150, 60, 0.1)),
        "repair": _concat(_tone(300, 900, 0.08), _tone(900, 1200, 0.05)),
        "thrust": _noise(0.25, 0.35, 0.2, rumble=True),
        "science": _concat(_tone(784, 784, 0.06), _tone(1175, 1175, 0.06), _tone(1568, 1568, 0.12)),
        "type": _tone(1200, 1200, 0.015, vol=0.25),
        "whoosh": _noise(0.6, 0.5, 2.0),
        "coin": _concat(_tone(988, 988, 0.06), _tone(1319, 1319, 0.2)),
    }


TRACKS = {"menu": make_menu_theme, "mission": make_mission_theme, "ending": make_ending_theme}


def bundled(name):
    """Path of a ready-made .ogg in sounds/ (e.g. 'sfx_click'), or None."""
    p = os.path.join(BUNDLED_SOUND_DIR, name + ".ogg")
    return p if os.path.exists(p) else None


def ensure_assets(progress=None):
    """Generate any missing .wav files. progress(text) is called for feedback.
    Skipped when the ready-made sounds/ folder is present (always in the web build)."""
    if bundled("sfx_click") and bundled("music_menu"):
        return
    os.makedirs(SOUND_DIR, exist_ok=True)
    sfx_needed = any(not os.path.exists(os.path.join(SOUND_DIR, "sfx_%s.wav" % k))
                     for k in ("click", "launch", "coin"))
    if sfx_needed:
        if progress:
            progress("Synthesising sound effects...")
        for name, buf in make_sfx().items():
            _write(os.path.join(SOUND_DIR, "sfx_%s.wav" % name), buf)
    for name, fn in TRACKS.items():
        path = os.path.join(SOUND_DIR, "music_%s.wav" % name)
        if not os.path.exists(path):
            if progress:
                progress("Composing %s music..." % name)
            _write(path, fn())


class Audio:
    def __init__(self, save):
        self.save = save
        self.ok = False
        self.sounds = {}
        self.current = None
        try:
            pygame.mixer.init(RATE, -16, 2, 512)
            self.ok = True
        except Exception:
            print("Audio disabled (no audio device).")

    def load(self):
        if not self.ok:
            return
        folder, ext = (BUNDLED_SOUND_DIR, ".ogg") if bundled("sfx_click") else (SOUND_DIR, ".wav")
        try:
            files = os.listdir(folder)
        except OSError:
            files = []
        for f in files:
            if f.startswith("sfx_") and f.endswith(ext):
                try:
                    self.sounds[f[4:-len(ext)]] = pygame.mixer.Sound(os.path.join(folder, f))
                except Exception:
                    pass
        self.apply_volume()

    def apply_volume(self):
        if not self.ok:
            return
        pygame.mixer.music.set_volume(self.save.data["music_volume"])
        for s in self.sounds.values():
            s.set_volume(self.save.data["sfx_volume"])

    def play(self, name, loops=0):
        s = self.sounds.get(name)
        if s:
            try:
                s.play(loops)
            except Exception:
                pass
        return s

    def stop(self, name):
        s = self.sounds.get(name)
        if s:
            s.stop()

    def music(self, name):
        if not self.ok or self.current == name:
            return
        self.current = name
        try:
            path = bundled("music_" + name) or os.path.join(SOUND_DIR, "music_%s.wav" % name)
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.save.data["music_volume"])
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    def stop_music(self, fade=800):
        if self.ok:
            pygame.mixer.music.fadeout(fade)
            self.current = None
