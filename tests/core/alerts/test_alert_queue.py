import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.alerts.alert_queue import AlertQueue


class TestAlertQueue(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.slept: list[float] = []
        self.gate = asyncio.Event()  # an alert stays until the test lets it go
        self.queue = AlertQueue(gap=0.5, sleep=self._sleep)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def _sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        await self.gate.wait()
        self.gate.clear()

    async def _turn(self) -> None:
        for _ in range(5):
            await asyncio.sleep(0)

    async def test_alerts_play_one_after_the_other_to_every_overlay(self) -> None:
        first, second = self.queue.listen(), self.queue.listen()
        self.assertEqual(self.queue.overlays, 2)
        self.assertEqual(await self.queue.show(Alert("one", seconds=3)), 0)
        self.assertEqual(await self.queue.show(Alert("two", seconds=200)), 1)  # one in front of it
        await self._turn()
        self.assertEqual((first.qsize(), second.qsize()), (1, 1))  # "two" waits its turn
        sent = first.get_nowait()
        self.assertEqual((sent["type"], sent["alert"]["text"], sent["alert"]["seconds"]), ("alert", "one", 3))
        self.gate.set()
        await self._turn()
        self.assertEqual(first.get_nowait()["alert"]["text"], "two")
        self.assertEqual(self.slept, [3.5, 120.5])  # its seconds + the gap; 200 s is cut to two minutes
        self.gate.set()
        await self._turn()
        self.assertEqual(await self.queue.show(Alert("three")), 0)  # the line was empty again

    async def test_a_preview_page_gets_alerts_but_isnt_counted_as_obs(self) -> None:
        preview = self.queue.listen(preview=True)
        self.assertEqual(self.queue.overlays, 0)
        await self.queue.show(Alert("one", message="hello there"))
        await self._turn()
        self.assertEqual(preview.get_nowait()["alert"]["message"], "hello there")
        self.queue.stop_listening(preview)
        self.queue.listen()
        self.assertEqual(self.queue.overlays, 1)

    async def test_waiting_for_an_alert_ends_when_it_was_shown(self) -> None:
        shown = asyncio.create_task(self.queue.show(Alert("one"), wait=True))
        await self._turn()
        self.assertFalse(shown.done())
        self.gate.set()
        self.assertEqual(await shown, 0)

    async def test_files_get_a_random_name_that_only_stands_for_them(self) -> None:
        picture, sound = self.folder / "party.GIF", self.folder / "ding.ogg"
        picture.write_bytes(b"gif")
        sound.write_bytes(b"ogg")
        inbox = self.queue.listen()
        await self.queue.show(Alert("hi", str(picture), str(sound), highlights=("", "Dragon")))
        await self._turn()
        alert = inbox.get_nowait()["alert"]
        self.assertTrue(alert["image"].startswith("/overlay/file/") and alert["image"].endswith(".gif"))
        self.assertEqual((alert["video"], alert["highlights"]), (False, ["Dragon"]))
        self.assertEqual(alert["look"], {})  # the start look: nothing to tell the page
        self.assertEqual(self.queue.file(alert["image"].rsplit("/", 1)[1]), picture)
        self.assertEqual(self.queue.file(alert["sound"].rsplit("/", 1)[1]), sound)
        self.assertIsNone(self.queue.file("../toolbox.toml"))
        self.assertNotIn(str(self.folder), str(alert))  # no path of this PC goes to the page

    async def test_a_file_that_isnt_there_fails_before_the_line(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "picture isn't there"):
            await self.queue.show(Alert("hi", str(self.folder / "gone.png")))
        self.assertEqual(self.queue.waiting, 0)

    async def test_old_file_names_stop_working(self) -> None:
        queue = AlertQueue(gap=0, sleep=self._sleep, keep_files=2)
        inbox = queue.listen()
        for name in ("a.png", "b.png", "c.png"):
            (self.folder / name).write_bytes(b"x")
            await queue.show(Alert(image=str(self.folder / name)))
            await self._turn()
            self.gate.set()
            await self._turn()
        urls = [inbox.get_nowait()["alert"]["image"].rsplit("/", 1)[1] for _ in range(3)]
        self.assertEqual([queue.file(u) is not None for u in urls], [False, True, True])

    async def test_clear_empties_the_line_and_tells_the_overlays(self) -> None:
        inbox = self.queue.listen()
        await self.queue.show(Alert("one"))
        waiting = asyncio.create_task(self.queue.show(Alert("two"), wait=True))
        await self._turn()
        self.assertEqual(self.queue.clear(), 2)
        await self._turn()
        self.assertTrue(waiting.done())  # nobody waits for an alert that was dropped
        self.assertEqual([inbox.get_nowait()["type"] for _ in range(2)], ["alert", "clear"])
        self.queue.stop_listening(inbox)
        self.assertEqual((self.queue.overlays, self.queue.waiting), (0, 0))
        self.assertEqual(await self.queue.show(Alert("three")), 0)  # and the line works again


if __name__ == "__main__":
    unittest.main()
