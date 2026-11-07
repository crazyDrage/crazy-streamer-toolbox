import time
from dataclasses import dataclass

from streamer_toolbox.core.system.backup_keeping import BackupKeeping


@dataclass(frozen=True)
class BackupPolicy(BackupKeeping):
    """Which backups of the settings folder are kept (his round 84: "10 daily ones, and 10 monthly ones"): the
    newest of each of the last `daily` days that have one, and the newest of each of the last `monthly` months.
    The newest backup of all is always kept."""

    daily: int = 10
    monthly: int = 10

    def keep(self, made: dict[str, float]) -> set[str]:
        """Of the backups (name → when it was made, seconds), the names to keep."""
        newest_first = sorted(made, key=lambda name: made[name], reverse=True)
        kept = set(newest_first[:1])
        for count, pattern in ((self.daily, "%Y-%m-%d"), (self.monthly, "%Y-%m")):
            seen: list[str] = []
            for name in newest_first:
                period = time.strftime(pattern, time.localtime(made[name]))
                if period in seen:
                    continue
                if len(seen) >= max(0, count):
                    break
                seen.append(period)
                kept.add(name)
        return kept
