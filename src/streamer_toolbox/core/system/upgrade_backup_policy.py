import time
from dataclasses import dataclass

from streamer_toolbox.core.system.backup_keeping import BackupKeeping

DAY = 24 * 60 * 60  # seconds


@dataclass(frozen=True)
class UpgradeBackupPolicy(BackupKeeping):
    """Which backups made before a settings upgrade are kept (his words, 2026-11-05: "keep the last 5 setting
    versions, and the first one of a day. Just in case we have 5+ version updates in one day"): the `last` newest,
    and the first of every day that has one within `days` days of the newest backup ("30 days is fine"), so the
    settings as they were before that day's upgrades stay."""

    last: int = 5
    days: int = 30

    def keep(self, made: dict[str, float]) -> set[str]:
        newest_first = sorted(made, key=lambda name: made[name], reverse=True)
        kept = set(newest_first[:max(0, self.last)])
        if not newest_first:
            return kept
        # whole days back from the newest one's (prune runs right after a new one is made: its day is today)
        oldest_day = _day(made[newest_first[0]] - self.days * DAY)
        first_of_day: dict[str, str] = {}
        for name in reversed(newest_first):  # oldest first: the first one seen of a day is its first
            if _day(made[name]) > oldest_day:
                first_of_day.setdefault(_day(made[name]), name)
        return kept | set(first_of_day.values())


def _day(seconds: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(seconds))
