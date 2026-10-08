import tempfile
import time
import unittest
from pathlib import Path

from streamer_toolbox.core.history.event_history import EventHistory

# a Wednesday noon in the PC's own time, so "this week" started two days before and "this month" on the 1st
NOW = time.mktime((2026, 10, 14, 12, 0, 0, 0, 0, -1))
DAY = 86400


class TestEventHistory(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "history" / "events.jsonl"
        self.now = NOW

    def tearDown(self) -> None:
        self._dir.cleanup()

    def history(self) -> EventHistory:
        return EventHistory(self.path, lambda: self.now)

    def test_sums_per_session_week_month_and_in_all_and_who_gave_most(self) -> None:
        history = self.history()
        history.record("cheer", "Ann", 100, at=NOW - 60 * DAY)  # long ago
        history.record("cheer", "Ann", 50, at=NOW - 10 * DAY)   # this month, not this week
        history.record("cheer", "Bob", 120, at=NOW - 1 * DAY)   # this week
        history.record("cheer", "Ann", 30, tier="x")            # now: this session
        history.record("follower", "Cy")
        cheers = history.summary("cheer")
        self.assertEqual((cheers["total"], cheers["month"], cheers["week"], cheers["session"]), (
            {"count": 4, "amount": 300}, {"count": 3, "amount": 200}, {"count": 2, "amount": 150},
            {"count": 1, "amount": 30}))
        self.assertEqual(cheers["top"]["alltime"], {"giver": {"name": "Ann", "amount": 180},
                                                    "biggest": {"name": "Bob", "amount": 120}})
        self.assertEqual(cheers["top"]["weekly"]["giver"], {"name": "Bob", "amount": 120})
        self.assertEqual(cheers["top"]["session"]["biggest"], {"name": "Ann", "amount": 30})
        self.assertEqual(history.summary("follower")["total"], {"count": 1, "amount": 0})
        self.assertEqual(history.summary("raid")["top"]["alltime"]["giver"], {"name": "", "amount": 0})
        self.assertEqual([entry["name"] for entry in history.recent("cheer")], ["Ann", "Bob", "Ann"])  # 40 days
        self.assertEqual(history.recent("cheer", 1)[0]["tier"], "x")

    def test_it_is_all_there_again_after_a_restart_and_the_session_starts_new(self) -> None:
        history = self.history()
        history.record("tip", "Ann", 2.5)
        history.record("tip", "Bob", 4)
        with self.path.open("a", encoding="utf-8") as file:
            file.write('{"kind": "tip", "name": "half a li')  # the PC lost power mid-line
        self.now += 3600
        again = self.history()
        tips = again.summary("tip")
        self.assertEqual((tips["total"], tips["session"], tips["week"]["amount"]),
                         ({"count": 2, "amount": 6.5}, {"count": 0, "amount": 0}, 6.5))
        self.assertTrue(again.known("tip"))
        self.assertFalse(again.known("raid"))
        self.assertEqual(EventHistory().summary("tip")["total"]["count"], 0)  # without a file: nothing kept

    def test_what_was_before_is_carried_over_once(self) -> None:
        history = self.history()
        self.assertTrue(history.carry("cheer", count=40, amount=1101, top_giver={"name": "Ann", "amount": 500},
                                      biggest={"name": "Bob", "amount": 300}))
        self.assertFalse(history.carry("cheer", count=40, amount=1101))  # a second import adds nothing
        history.record("cheer", "Old", 25, at=NOW - 2 * DAY, counted=False)  # brought over with its date
        history.record("cheer", "Ann", 10)
        cheers = self.history().summary("cheer")  # read back from the file
        self.assertEqual((cheers["total"], cheers["week"]), ({"count": 41, "amount": 1111},
                                                             {"count": 2, "amount": 35}))
        self.assertEqual(cheers["top"]["alltime"], {"giver": {"name": "Ann", "amount": 510},
                                                    "biggest": {"name": "Bob", "amount": 300}})
        self.assertTrue(history.carried("cheer"))
        self.assertFalse(history.carried("tip"))


if __name__ == "__main__":
    unittest.main()
