import tempfile
import threading
import unittest
from pathlib import Path

from streamer_toolbox.gui.services.app_window_page_opener import (DEFAULT_BROWSERS, AppWindowPageOpener,
                                                                 installed_browsers)
from tests.fakes.fake_browser_process import FakeBrowserProcess
from tests.fakes.fake_page_opener import FakePageOpener


class TestAppWindowPageOpener(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.launched: list[list[str]] = []
        self.fallback = FakePageOpener()

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_first_installed_browser_opens_app_window(self) -> None:
        chrome = self.folder / "chrome.exe"
        chrome.touch()
        opener = AppWindowPageOpener(self.fallback, [self.folder / "msedge.exe", chrome], self.launched.append)
        opener.open("http://127.0.0.1:8850")
        self.assertEqual(self.launched, [[str(chrome), "--app=http://127.0.0.1:8850", "--window-size=1280,800"]])
        self.assertEqual(self.fallback.opened, [])

    def test_own_profile_closing_the_window_runs_on_closed(self) -> None:
        chrome = self.folder / "chrome.exe"
        chrome.touch()
        process = FakeBrowserProcess()
        closed = threading.Event()

        def launch(command: list[str]) -> FakeBrowserProcess:
            self.launched.append(command)
            return process

        opener = AppWindowPageOpener(self.fallback, [chrome], launch, profile_dir=self.folder / "window",
                                     on_closed=closed.set)
        opener.open("http://127.0.0.1:8850")
        self.assertIn(f"--user-data-dir={self.folder / 'window'}", self.launched[0])
        self.assertFalse(closed.wait(0.05))
        process.close()
        self.assertTrue(closed.wait(2))

    def test_no_browser_uses_fallback(self) -> None:
        opener = AppWindowPageOpener(self.fallback, [self.folder / "msedge.exe"], self.launched.append)
        opener.open("http://127.0.0.1:8850")
        self.assertEqual(self.launched, [])
        self.assertEqual(self.fallback.opened, ["http://127.0.0.1:8850"])

    def test_browsers_are_also_found_by_their_command_as_on_linux(self) -> None:
        on_path = {"chromium": "/usr/bin/chromium", "brave-browser": "/usr/bin/brave-browser"}
        found = installed_browsers(on_path.get)
        self.assertEqual(found[:len(DEFAULT_BROWSERS)], DEFAULT_BROWSERS)
        self.assertEqual(found[len(DEFAULT_BROWSERS):], (Path("/usr/bin/chromium"), Path("/usr/bin/brave-browser")))
        self.assertEqual(installed_browsers(lambda command: None), DEFAULT_BROWSERS)


if __name__ == "__main__":
    unittest.main()
