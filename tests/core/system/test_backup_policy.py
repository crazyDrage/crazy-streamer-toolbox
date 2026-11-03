import time
import unittest

from streamer_toolbox.core.system.backup_policy import BackupPolicy


def at(day: str, clock: str = "12:00") -> float:
    return time.mktime(time.strptime(f"{day} {clock}", "%Y-%m-%d %H:%M"))


class TestBackupPolicy(unittest.TestCase):
    """His round 84: "10 daily ones, and 10 monthly ones"."""

    def test_newest_of_each_day_and_of_each_month(self) -> None:
        made = {"a": at("2026-11-03", "20:00"), "b": at("2026-11-03", "08:00"), "c": at("2026-11-02"),
                "d": at("2026-10-31"), "e": at("2026-10-01"), "f": at("2026-09-15"), "g": at("2026-09-01")}
        self.assertEqual(BackupPolicy(daily=2, monthly=2).keep(made), {"a", "c", "d"})
        self.assertEqual(BackupPolicy(daily=1, monthly=3).keep(made), {"a", "d", "f"})

    def test_the_newest_stays_even_with_nothing_to_keep(self) -> None:
        made = {"old": at("2026-01-01"), "new": at("2026-02-01")}
        self.assertEqual(BackupPolicy(daily=0, monthly=0).keep(made), {"new"})
        self.assertEqual(BackupPolicy().keep({}), set())


if __name__ == "__main__":
    unittest.main()
