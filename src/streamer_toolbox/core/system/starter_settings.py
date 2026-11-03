import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from streamer_toolbox.core.system.backup_policy import BackupPolicy

FILE = "starter.json"  # in the settings folder; the starter window is where it is changed (rule: no files)
OPEN_MODES = {"window": "Own window", "lean-window": "Own window, less memory", "browser": "Browser tab",
              "none": "No window"}


@dataclass
class StarterSettings:
    """What the starter remembers (his round 84): how the toolbox opens, whether it starts like that without
    asking, whether closing the toolbox's window stops it, and the backups (one a day when it starts, the
    question when it closes, how many daily and monthly ones are kept)."""

    open_mode: str = "window"
    start_without_asking: bool = False
    close_stops: bool = True
    backup_on_start: bool = True
    ask_backup_on_close: bool = True  # his round 84: "Backup now?" when closing
    daily: int = 10
    monthly: int = 10

    @property
    def policy(self) -> BackupPolicy:
        return BackupPolicy(self.daily, self.monthly)

    @classmethod
    def read(cls, settings: Path) -> "StarterSettings":
        try:
            data = json.loads((settings / FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in fields(cls)}
        read = cls(**{k: v for k, v in data.items() if k in known}) if isinstance(data, dict) else cls()
        if read.open_mode not in OPEN_MODES:
            read.open_mode = "window"
        read.daily, read.monthly = max(0, int(read.daily)), max(0, int(read.monthly))
        return read

    def write(self, settings: Path) -> None:
        """Written whole to a temp file, then swapped in: a backup or a crash never sees half a file."""
        settings.mkdir(parents=True, exist_ok=True)
        temp = settings / (FILE + ".tmp")
        temp.write_text(json.dumps(asdict(self), indent=1), encoding="utf-8")
        os.replace(temp, settings / FILE)
