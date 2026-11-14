import sys
import unittest
from unittest.mock import patch

from streamer_toolbox.gui.services.toolbox_tray import ToolboxTray


class TestToolboxTray(unittest.TestCase):
    """The toolbox's tray icon: open (the double click's), restart, stop; no tray is no problem."""

    def setUp(self) -> None:
        self.done: list[str] = []
        self.tray = ToolboxTray("http://127.0.0.1:8850", lambda: self.done.append("restart"),
                                lambda: self.done.append("stop"), open_page=lambda url: self.done.append(url))

    def test_the_menu_opens_restarts_and_stops(self) -> None:
        items = self.tray.items()
        self.assertEqual([("Open the toolbox", True), ("Restart the toolbox", False), ("Stop the toolbox", False)],
                         [(text, default) for text, _, default in items])
        for _, action, _ in items:
            action()
        self.assertEqual(["http://127.0.0.1:8850", "restart", "stop"], self.done)

    def test_without_a_tray_the_toolbox_still_runs(self) -> None:
        with patch.dict(sys.modules, {"pystray": None}):  # not installed / no tray on this desktop
            self.assertFalse(self.tray.start())
        self.tray.stop()  # nothing to stop: no error
        self.assertEqual([], self.done)


if __name__ == "__main__":
    unittest.main()
