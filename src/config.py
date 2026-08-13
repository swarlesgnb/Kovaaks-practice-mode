import json
import os
from pathlib import Path

APPDATA = Path(os.environ.get("APPDATA", str(Path.home())))
CONFIG_DIR = APPDATA / "KovaaksPracticeMode"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "practice_mode_enabled": False,
    "cover_label": "PRACTICE MODE",
    "hotkey": "ctrl+alt+p",
    # regions are stored as fractions (0..1) of the KovaaK's client area,
    # so one calibration keeps working across window moves/resizes at the
    # same aspect ratio.
    "regions": [],
    # Same format, but these mark button zones (Play/Next/Replay/scenario
    # list) - clicking inside one ends the post-run results-visible window
    # immediately instead of waiting out the fallback timeout.
    "trigger_regions": [],
}


class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                    loaded = json.load(f)
                self.data.update(loaded)
            except Exception:
                pass

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    @property
    def practice_mode_enabled(self):
        return self.data["practice_mode_enabled"]

    @practice_mode_enabled.setter
    def practice_mode_enabled(self, value):
        self.data["practice_mode_enabled"] = bool(value)
        self.save()

    @property
    def regions(self):
        return self.data["regions"]

    def set_regions(self, regions):
        self.data["regions"] = regions
        self.save()

    @property
    def trigger_regions(self):
        return self.data.get("trigger_regions", [])

    def set_trigger_regions(self, trigger_regions):
        self.data["trigger_regions"] = trigger_regions
        self.save()

    @property
    def hotkey(self):
        return self.data.get("hotkey", "ctrl+alt+p")
