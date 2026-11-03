import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.system.starter_settings import StarterSettings
from streamer_toolbox.starter.starter_app import StarterApp
from tests.fakes.fake_toolbox_launcher import FakeToolboxLauncher


class TestStarterApp(unittest.TestCase):
    """His round 84: the starter starts the toolbox the chosen way and makes the daily backup first."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.settings = Path(self._dir.name)
        (self.settings / "toolbox.toml").write_text('[api]\nhost = "0.0.0.0"\nport = 8851\n', encoding="utf-8")
        self.made: list[FakeToolboxLauncher] = []

    def tearDown(self) -> None:
        self._dir.cleanup()

    def app(self) -> StarterApp:
        def make(*args, **kwargs) -> FakeToolboxLauncher:
            self.made.append(FakeToolboxLauncher(*args, **kwargs))
            return self.made[-1]
        return StarterApp(self.settings, Path("plugins"), Path("."), make_launcher=make)

    def test_starts_the_toolbox_after_the_daily_backup(self) -> None:
        StarterSettings(open_mode="none").write(self.settings)
        app = self.app()
        self.assertEqual(app.url, "http://127.0.0.1:8851")  # 0.0.0.0 is opened on this PC
        app.start()
        app._thread.join(2)
        launcher = self.made[0]
        self.assertIn("--child", launcher.command)
        self.assertIn(str(self.settings.resolve() / "toolbox.toml"), launcher.command)
        self.assertIsNone(launcher.opener)  # No window
        self.assertEqual(len(app.backup.all()), 1)
        app.start()  # a second start the same day: no second backup
        app._thread.join(2)
        self.assertEqual(len(app.backup.all()), 1)

    def test_no_daily_backup_when_switched_off_and_the_choice_is_kept(self) -> None:
        StarterSettings(open_mode="browser", backup_on_start=False).write(self.settings)
        app = self.app()
        app.start()
        app._thread.join(2)
        self.assertEqual(app.backup.all(), [])
        self.assertEqual(type(self.made[0].opener).__name__, "BrowserPageOpener")
        self.assertEqual(StarterSettings.read(self.settings).open_mode, "browser")


if __name__ == "__main__":
    unittest.main()
