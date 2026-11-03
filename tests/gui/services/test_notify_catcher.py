import tempfile
import unittest
from pathlib import Path

from nicegui import ui

from streamer_toolbox.gui.services.message_log import MessageLog
from streamer_toolbox.gui.services.notify_catcher import NotifyCatcher


class TestNotifyCatcher(unittest.TestCase):
    """Every ui.notify lands in the Debug list (his round 81), also one without a page around it."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self._original = ui.notify
        self.messages = MessageLog(Path(self._dir.name) / "messages.json")
        self.catcher = NotifyCatcher(self.messages)

    def tearDown(self) -> None:
        ui.notify = self._original
        self._dir.cleanup()

    def test_every_notify_goes_into_the_list(self) -> None:
        self.catcher.install()
        ui.notify("Saved", type="positive")
        ui.notify("Not frozen", caption="no OBS", type="negative")
        ui.notify("plain")
        self.assertEqual([(e.kind, e.text) for e in self.messages.entries()],
                         [("info", "plain"), ("negative", "Not frozen\nno OBS"), ("positive", "Saved")])


if __name__ == "__main__":
    unittest.main()
