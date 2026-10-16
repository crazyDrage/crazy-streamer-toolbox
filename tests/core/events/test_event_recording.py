import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from streamer_toolbox.core.events.event_recording import ON_KEY, EventRecording

NOON = datetime(2026, 10, 11, 12, 0, 0).timestamp()


class EventRecordingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.folder = Path(self._temp.name) / "events"

    def lines(self, name: str = "2026-10-11.jsonl") -> list[dict]:
        return [json.loads(line) for line in (self.folder / name).read_text(encoding="utf-8").splitlines()]

    async def test_every_event_is_a_line_in_the_days_file(self) -> None:
        recording = EventRecording(self.folder, {ON_KEY: True}, clock=lambda: NOON)
        await recording.handle("twitch.chat", {"user": "ann", "message": "hi"})
        await recording.handle("twitch.chat", {"user": "ann", "message": "hi"})
        await recording.handle("twitch.follow", {"user": "bob"})

        lines = self.lines()
        self.assertEqual(["twitch.chat", "twitch.chat", "twitch.follow"], [line["trigger"] for line in lines])
        self.assertEqual({"user": "ann", "message": "hi"}, lines[0]["data"])
        self.assertTrue(lines[0]["at"].startswith("2026-10-11T12:00:00"))
        self.assertNotIn("raw", lines[0])

    async def test_the_platforms_message_goes_with_its_event_once(self) -> None:
        recording = EventRecording(self.folder, {ON_KEY: True}, clock=lambda: NOON)
        recording.raw("twitch.gift", {"total": 5})
        await recording.handle("twitch.gift", {"user": "ann", "amount": 5})
        await recording.handle("twitch.gift", {"user": "bob", "amount": 1})

        lines = self.lines()
        self.assertEqual({"total": 5}, lines[0]["raw"])
        self.assertNotIn("raw", lines[1])

    async def test_timer_ticks_are_left_out(self) -> None:
        recording = EventRecording(self.folder, {ON_KEY: True}, clock=lambda: NOON)
        await recording.handle("timer", {"every": "1"})

        self.assertFalse((self.folder / "2026-10-11.jsonl").exists())

    async def test_a_new_day_gets_a_new_file(self) -> None:
        now = [NOON]
        recording = EventRecording(self.folder, {ON_KEY: True}, clock=lambda: now[0])
        await recording.handle("twitch.follow", {"user": "ann"})
        now[0] += 86400
        await recording.handle("twitch.follow", {"user": "bob"})

        self.assertEqual("ann", self.lines()[0]["data"]["user"])
        self.assertEqual("bob", self.lines("2026-10-12.jsonl")[0]["data"]["user"])

    async def test_old_day_files_are_removed_at_start(self) -> None:
        self.folder.mkdir(parents=True)
        (self.folder / "2026-08-01.jsonl").write_text("{}\n", encoding="utf-8")
        (self.folder / "2026-10-01.jsonl").write_text("{}\n", encoding="utf-8")
        (self.folder / "notes.txt").write_text("his", encoding="utf-8")

        EventRecording(self.folder, {ON_KEY: True}, clock=lambda: NOON)

        self.assertEqual(["2026-10-01.jsonl", "notes.txt"], sorted(file.name for file in self.folder.iterdir()))

    async def test_off_until_switched_on_and_the_switch_counts_at_once(self) -> None:
        choice: dict = {}
        recording = EventRecording(self.folder, choice, clock=lambda: NOON)
        recording.raw("twitch.follow", {"old": True})
        await recording.handle("twitch.follow", {"user": "ann"})
        self.assertFalse(recording.on)
        self.assertFalse(self.folder.exists())

        recording.set_on(True)
        await recording.handle("twitch.follow", {"user": "bob"})
        recording.set_on(False)
        await recording.handle("twitch.follow", {"user": "cid"})

        self.assertEqual({ON_KEY: False}, choice)
        self.assertEqual([{"user": "bob"}], [line["data"] for line in self.lines()])
        self.assertNotIn("raw", self.lines()[0])
        self.assertEqual(1, recording.size()[0])


if __name__ == "__main__":
    unittest.main()
