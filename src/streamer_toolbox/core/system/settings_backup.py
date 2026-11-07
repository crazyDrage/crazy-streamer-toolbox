import logging
import time
import zipfile
from collections.abc import Callable
from pathlib import Path

from streamer_toolbox.core.system.backup_keeping import BackupKeeping

log = logging.getLogger(__name__)

BACKUPS = "backups"  # in the settings folder
UPGRADES = "upgrades"  # in backups/: the copies made before a settings upgrade (SettingsUpgrades)
NOT_BACKED_UP = ("cache", BACKUPS, "app_window")  # downloads, the backups themselves, the window's browser data


class SettingsBackup:
    """A zip of the settings folder in its backups/ folder (his round 84: a backup button in the starter, and the
    copy before each update): everything but the downloads, the backups and the window's browser data. Unpack
    it over the settings folder to go back. Each zip is checked after it is written (every file read back);
    prune() keeps what the BackupPolicy says, the rest of the zips in backups/ go.

    vtuber_backup (the PC backup) takes the settings folder with these zips along, so they stay here.

    `sub`: a folder of its own inside backups/ (the ones made before a settings upgrade: backups/upgrades/), so
    one kind's prune never takes the other kind's zips."""

    def __init__(self, settings: Path, now: Callable[[], float] = time.time, sub: str = "") -> None:
        self._settings = settings
        self._now = now
        self._sub = sub

    @property
    def folder(self) -> Path:
        return self._settings / BACKUPS / self._sub if self._sub else self._settings / BACKUPS

    def make(self, prefix: str = "settings") -> Path:
        """<prefix>-<date>_<time>.zip; a broken zip is deleted and raises."""
        stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(self._now()))
        target = self.folder / f"{prefix}-{stamp}.zip"
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as packed:
            for file in sorted(self._settings.rglob("*")):
                relative = file.relative_to(self._settings)
                if file.is_file() and relative.parts[0] not in NOT_BACKED_UP:
                    try:
                        packed.write(file, relative)
                    except PermissionError:  # held open by another program: the rest still goes in
                        log.warning("not in the backup (in use): %s", relative)
        with zipfile.ZipFile(target) as packed:
            broken = packed.testzip()
        if broken is not None:
            target.unlink(missing_ok=True)
            raise OSError(f"the backup came out broken at {broken}: nothing was kept")
        log.info("settings backed up in %s", target)
        return target

    def all(self) -> list[Path]:
        """The zips in backups/, newest first."""
        if not self.folder.is_dir():
            return []
        return sorted(self.folder.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)

    def made_today(self) -> bool:
        today = time.strftime("%Y-%m-%d", time.localtime(self._now()))
        return any(time.strftime("%Y-%m-%d", time.localtime(p.stat().st_mtime)) == today for p in self.all())

    def prune(self, policy: BackupKeeping) -> list[Path]:
        """Deletes the zips the policy doesn't keep; gives them."""
        zips = {p.name: p for p in self.all()}
        kept = policy.keep({name: path.stat().st_mtime for name, path in zips.items()})
        gone = [path for name, path in zips.items() if name not in kept]
        for path in gone:
            path.unlink(missing_ok=True)
        return gone
