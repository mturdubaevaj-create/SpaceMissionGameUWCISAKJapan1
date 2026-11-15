"""Persistent save data (progress, settings, player name, learned facts)."""
import json
import os

from settings import SAVE_FILE

DEFAULT = {
    "player_name": "",
    "unlocked": ["moon"],
    "completed": [],
    "music_volume": 0.6,
    "sfx_volume": 0.8,
    "seen_tips": [],
    "known_facts": [],
    "best_scores": {},
    "game_finished": False,
}


class SaveData:
    def __init__(self, path=SAVE_FILE):
        self.path = path
        self.data = json.loads(json.dumps(DEFAULT))
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self.data.update(json.load(f))
            except (OSError, ValueError):
                pass

    def save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self.data, f, indent=1)
        except OSError:
            pass

    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v
        self.save()

    def reset_progress(self):
        keep = {k: self.data[k] for k in ("music_volume", "sfx_volume")}
        self.data = json.loads(json.dumps(DEFAULT))
        self.data.update(keep)
        self.save()
