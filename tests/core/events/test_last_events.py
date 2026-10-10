import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.events.last_events import LastEvents


class TestLastEvents(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name) / "last_triggers"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _file(self, name: str) -> dict:
        return json.loads((self.folder / name).read_text(encoding="utf-8"))

    async def test_the_last_one_is_a_file_with_the_data_and_the_raw_message(self) -> None:
        last = LastEvents(self.folder, delay=0.01)
        last.raw("twitch.gift", {"user_name": "Santa", "total": 5, "cumulative_total": 20})
        await last.handle("twitch.gift", {"user": "Santa", "amount": 5})
        await last.handle("timer", {"every": 1})
        await asyncio.sleep(0.05)
        gift = self._file("twitch.gift.json")
        self.assertEqual((gift["trigger"], gift["data"], gift["raw"]["cumulative_total"]),
                         ("twitch.gift", {"user": "Santa", "amount": 5}, 20))
        self.assertTrue(gift["at"].startswith("20"))
        self.assertNotIn("raw", self._file("timer.json"))  # nobody handed one over

    async def test_many_in_a_row_are_one_write_of_the_newest_and_the_same_again_is_none(self) -> None:
        last = LastEvents(self.folder, delay=0.05)
        for name in ("A", "B", "C"):
            await last.handle("twitch.sub", {"user": name})
        self.assertFalse(self.folder.exists())  # not yet
        self.assertEqual(last.get("twitch.sub"), {"user": "C"})
        last.flush()
        self.assertEqual(self._file("twitch.sub.json")["data"], {"user": "C"})
        written = self._file("twitch.sub.json")["at"]
        (self.folder / "twitch.sub.json").write_text("{}", encoding="utf-8")
        await last.handle("twitch.sub", {"user": "C"})  # a timer's tick: the same data
        last.flush()
        self.assertEqual(self._file("twitch.sub.json"), {})
        self.assertTrue(written)

    async def test_it_is_still_known_after_a_restart_and_odd_names_are_safe_file_names(self) -> None:
        first = LastEvents(self.folder, delay=0.01)
        await first.handle("plugin/odd:name", {"user": "Kit"})
        first.flush()
        again = LastEvents(self.folder)
        self.assertEqual(again.path("plugin/odd:name").name, "plugin_odd_name.json")
        self.assertEqual(again.get("plugin/odd:name"), {"user": "Kit"})
        self.assertIsNone(again.get("twitch.raid"))


if __name__ == "__main__":
    unittest.main()
