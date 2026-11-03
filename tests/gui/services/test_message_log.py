import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.gui.services.activity_log import ActivityLog
from streamer_toolbox.gui.services.message_log import MessageLog


class TestMessageLog(unittest.TestCase):
    """The info bar's Debug list (his round 81): newest first, flow runs from the ActivityLog, the last 10 kept."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "cache" / "messages.json"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_newest_first_and_runs_from_the_activity_log(self) -> None:
        messages = MessageLog(self.path)
        activity = ActivityLog(on_add=messages.activity)
        messages.add("positive", "Saved")
        activity.add("twitch.cheer", "flow.twitch_thank_cheer", True, None)
        activity.add("GUI", "flow.so", False, "box thank (twitch.send_chat): not logged in")
        self.assertEqual([(e.kind, e.text) for e in messages.entries()], [
            ("negative", "GUI · flow.so: box thank (twitch.send_chat): not logged in"),
            ("run", "twitch.cheer · flow.twitch_thank_cheer: done"),
            ("positive", "Saved")])
        self.assertEqual(messages.version, 3)
        self.assertEqual(len(activity.entries()), 2)  # the Live page's Recent list still has them

    def test_the_last_ten_are_there_after_a_restart(self) -> None:
        messages = MessageLog(self.path, kept=10)
        for number in range(15):
            messages.add("info", f"line {number}")
        messages.save()
        again = MessageLog(self.path, kept=10)
        self.assertEqual([e.text for e in again.entries()], [f"line {n}" for n in range(14, 4, -1)])

    def test_clear_and_a_broken_file(self) -> None:
        messages = MessageLog(self.path)
        messages.add("info", "a")
        messages.clear()
        self.assertEqual(messages.entries(), [])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(MessageLog(self.path).entries(), [])


if __name__ == "__main__":
    unittest.main()
