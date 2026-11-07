import time
import unittest

from streamer_toolbox.core.system.upgrade_backup_policy import UpgradeBackupPolicy


def _at(day: int, hour: int) -> float:
    return time.mktime((2026, 11, day, hour, 0, 0, 0, 0, -1))


class TestUpgradeBackupPolicy(unittest.TestCase):
    """His words (2026-11-05): "keep the last 5 setting versions, and the first one of a day. Just in case we have
    5+ version updates in one day"."""

    def test_eight_upgrades_in_one_day_keep_the_last_five_and_the_first(self) -> None:
        made = {f"b{hour}": _at(5, hour) for hour in range(1, 9)}
        self.assertEqual(UpgradeBackupPolicy().keep(made), {"b1", "b4", "b5", "b6", "b7", "b8"})

    def test_the_first_of_every_day_stays_after_the_last_five_moved_on(self) -> None:
        made = {"mon_first": _at(2, 9), "mon_later": _at(2, 18), "tue_first": _at(3, 9),
                **{f"wed{hour}": _at(4, hour) for hour in range(10, 16)}}
        self.assertEqual(UpgradeBackupPolicy().keep(made),
                         {"mon_first", "tue_first", "wed10", "wed11", "wed12", "wed13", "wed14", "wed15"})

    def test_firsts_of_the_day_stay_30_days(self) -> None:
        """His answer: "30 days is fine"."""
        made = {"old": _at(1, 9), "old_later": _at(1, 18), "recent": _at(20, 9),
                **{f"new{hour}": time.mktime((2026, 12, 2, hour, 0, 0, 0, 0, -1)) for hour in range(10, 15)}}
        kept = UpgradeBackupPolicy().keep(made)  # Nov 1 is 31 days before Dec 2, Nov 20 isn't
        self.assertEqual(kept, {"recent", "new10", "new11", "new12", "new13", "new14"})

    def test_fewer_than_five_are_all_kept(self) -> None:
        made = {"a": _at(1, 1), "b": _at(1, 2)}
        self.assertEqual(UpgradeBackupPolicy().keep(made), {"a", "b"})


if __name__ == "__main__":
    unittest.main()
