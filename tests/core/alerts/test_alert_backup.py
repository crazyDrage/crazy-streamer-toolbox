import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.alerts.alert_backup import AlertBackup
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_store import AlertStore


class TestAlertBackup(unittest.IsolatedAsyncioTestCase):
    """His round 64: a restart clears the line, unless "Keep alerts through a restart" is on."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.gate = asyncio.Event()  # alerts stay until the test ends

    def tearDown(self) -> None:
        self.gate.set()
        self._dir.cleanup()

    async def _hold(self, seconds: float) -> None:
        await self.gate.wait()

    def _toolbox(self) -> tuple[AlertStore, AlertQueue, AlertBackup]:
        """One start of the toolbox: its store, line and backup, from the same folder."""
        store = AlertStore(self.folder / "alerts.json")
        queue = AlertQueue(sleep=self._hold)
        return store, queue, AlertBackup(self.folder / "alert_backup.json", store, queue)

    async def _turn(self) -> None:
        for _ in range(5):
            await asyncio.sleep(0)

    async def test_off_a_restart_clears_the_line_and_there_is_no_file(self) -> None:
        _, queue, backup = self._toolbox()
        backup.start()
        await queue.show(Alert(text="one"))
        await queue.show(Alert(text="two"))
        self.assertFalse((self.folder / "alert_backup.json").exists())
        _, again, backup = self._toolbox()
        backup.start()
        self.assertEqual(again.waiting, 0)

    async def test_on_the_waiting_alerts_and_the_numbers_go_on_after_a_restart(self) -> None:
        _, queue, backup = self._toolbox()
        backup.start()
        backup.switch(True)
        inbox = queue.listen()
        await queue.show(Alert(text="one"))
        await queue.show(Alert(text="two"))
        await queue.show(Alert(text="three"))
        await self._turn()
        first = inbox.get_nowait()
        run = queue.sent.run
        self.assertTrue(AlertStore(self.folder / "alerts.json").keep_through_restart)

        _, again, backup = self._toolbox()  # the toolbox starts again
        backup.start()
        self.assertEqual((again.sent.run, again.sent.last), (run, first["id"]))
        await self._turn()
        self.assertEqual(again.waiting, 1)  # "two" plays at once, "three" waits
        greeting = again.greeting(run, first["id"])
        self.assertEqual([m["alert"]["text"] for m in greeting[1:]], ["two"])
        self.assertEqual(greeting[1]["id"], first["id"] + 1)  # the numbers went on

    async def test_switching_off_removes_the_file(self) -> None:
        _, queue, backup = self._toolbox()
        backup.start()
        backup.switch(True)
        await queue.show(Alert(text="one"))
        self.assertIn("one", (self.folder / "alert_backup.log").read_text("utf-8"))
        backup.switch(False)
        self.assertFalse((self.folder / "alert_backup.json").exists())

    async def _kept(self, *texts: str) -> tuple[AlertQueue, AlertBackup]:
        """A toolbox with the backup on and these alerts in the line (nothing shown yet: no player turn)."""
        _, queue, backup = self._toolbox()
        backup.start()
        backup.switch(True)
        for text in texts:
            await queue.show(Alert(text=text))
        return queue, backup

    async def _restarted(self) -> AlertQueue:
        _, queue, backup = self._toolbox()
        backup.start()
        return queue

    def _texts(self, queue: AlertQueue) -> list[str]:
        return [alert["text"] for alert in queue.state()["waiting"]]

    async def test_a_change_is_one_line_in_the_log_not_the_whole_line_again(self) -> None:
        await self._kept("one", "two", "three")
        picture = json.loads((self.folder / "alert_backup.json").read_text("utf-8"))
        self.assertEqual(picture["waiting"], [])  # written when it was switched on
        lines = (self.folder / "alert_backup.log").read_text("utf-8").splitlines()
        self.assertEqual([json.loads(line)["add"]["text"] for line in lines], ["one", "two", "three"])

    async def test_the_log_comes_back_in_order_after_a_restart(self) -> None:
        await self._kept("one", "two", "three")
        await self._turn()  # "one" is showing now: it left the line
        self.assertEqual(self._texts(await self._restarted()), ["two", "three"])

    async def test_a_crash_between_the_picture_and_the_log_counts_nothing_twice(self) -> None:
        await self._kept("one", "two")  # the log: "one" (change 1), "two" (change 2)
        picture = json.loads((self.folder / "alert_backup.json").read_text("utf-8"))
        picture.update(waiting=[Alert(text="one").to_dict(), Alert(text="two").to_dict()], number=2)
        (self.folder / "alert_backup.json").write_text(json.dumps(picture), encoding="utf-8")  # new picture, old log
        self.assertEqual(self._texts(await self._restarted()), ["one", "two"])

    async def test_a_half_written_last_line_is_left_out(self) -> None:
        await self._kept("one", "two")
        with (self.folder / "alert_backup.log").open("a", encoding="utf-8") as file:
            file.write('{"add": {"text": "thr')
        self.assertEqual(self._texts(await self._restarted()), ["one", "two"])

    async def test_the_log_is_never_longer_than_the_line_or_100(self) -> None:
        queue, _ = await self._kept(*(f"alert {i}" for i in range(150)))
        queue.clear()  # 150 lines in the log, 0 in the line: the picture is written again, the log starts over
        await queue.show(Alert(text="after"))
        lines = (self.folder / "alert_backup.log").read_text("utf-8").splitlines()
        self.assertEqual([json.loads(line).get("add", {}).get("text") for line in lines], ["after"])
        self.assertEqual(json.loads((self.folder / "alert_backup.json").read_text("utf-8"))["waiting"], [])
        self.assertEqual(self._texts(await self._restarted()), ["after"])

    async def test_switching_off_removes_the_log_too(self) -> None:
        _, backup = await self._kept("one")
        backup.switch(False)
        self.assertFalse((self.folder / "alert_backup.log").exists())

    async def test_a_backup_from_before_the_log_still_comes_back(self) -> None:
        store, _, _ = self._toolbox()
        store.set_keep_through_restart(True)
        old = {"waiting": [Alert(text="one").to_dict(), Alert(text="two").to_dict()],
               "sent": {"run": "r1", "last": 4, "kept": []}, "files": {}}
        (self.folder / "alert_backup.json").write_text(json.dumps(old), encoding="utf-8")
        queue = await self._restarted()
        self.assertEqual(queue.sent.last, 4)
        self.assertEqual(self._texts(queue), ["one", "two"])

    async def test_a_broken_file_starts_an_empty_line(self) -> None:
        store, _, _ = self._toolbox()
        store.set_keep_through_restart(True)
        (self.folder / "alert_backup.json").write_text("{not json", encoding="utf-8")
        _, queue, backup = self._toolbox()
        backup.start()
        self.assertEqual(queue.waiting, 0)


if __name__ == "__main__":
    unittest.main()
