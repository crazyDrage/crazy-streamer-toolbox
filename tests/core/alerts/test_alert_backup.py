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
        self.assertIn("one", json.dumps(json.loads((self.folder / "alert_backup.json").read_text("utf-8"))))
        backup.switch(False)
        self.assertFalse((self.folder / "alert_backup.json").exists())

    async def test_a_broken_file_starts_an_empty_line(self) -> None:
        store, _, _ = self._toolbox()
        store.set_keep_through_restart(True)
        (self.folder / "alert_backup.json").write_text("{not json", encoding="utf-8")
        _, queue, backup = self._toolbox()
        backup.start()
        self.assertEqual(queue.waiting, 0)


if __name__ == "__main__":
    unittest.main()
