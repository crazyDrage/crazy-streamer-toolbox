import tempfile
import unittest
from pathlib import Path
from unittest import mock

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.upgrades import settings_upgrades
from streamer_toolbox.core.upgrades.settings_upgrades import SettingsUpgrades
from tests.fakes.fake_settings_upgrade import FakeSettingsUpgrade


class TestSettingsUpgrades(unittest.TestCase):
    """His next release plan, part 3: one number for the settings folder, one place that runs the upgrades."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.config = Path(self._dir.name) / "toolbox.toml"
        self.ran: list[int] = []
        patch = mock.patch.object(settings_upgrades, "SETTINGS_VERSION", 3)
        patch.start()
        self.addCleanup(patch.stop)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _upgrades(self) -> SettingsUpgrades:
        return SettingsUpgrades(self.config, [FakeSettingsUpgrade(v, self.ran) for v in (2, 1, 3)])

    def test_each_step_runs_once_in_order_and_the_number_is_kept(self) -> None:
        self.config.write_text("[api]\nport = 8862  # his port\n", encoding="utf-8")
        upgrades = self._upgrades()
        self.assertEqual(upgrades.version, 0)
        self.assertEqual(upgrades.run(), ["1 (fake): step 1", "2 (fake): step 2", "3 (fake): step 3"])
        self.assertEqual((self.ran, upgrades.version), ([1, 2, 3], 3))
        self.assertIn("port = 8862  # his port", self.config.read_text(encoding="utf-8"))
        self.assertEqual(self._upgrades().run(), [])
        self.assertEqual(self.ran, [1, 2, 3])

    def test_only_the_newer_steps_run(self) -> None:
        self.config.write_text("[toolbox]\nsettings_version = 2\n", encoding="utf-8")
        self._upgrades().run()
        self.assertEqual(self.ran, [3])

    def test_settings_from_a_newer_toolbox_stay_as_they_are(self) -> None:
        self.config.write_text("[toolbox]\nsettings_version = 9\n", encoding="utf-8")
        with self.assertLogs(settings_upgrades.log, "WARNING"):
            self.assertEqual(self._upgrades().run(), [])
        self.assertEqual((self.ran, self._upgrades().version, self._upgrades().newer), ([], 9, True))

    def test_an_imported_flow_gets_the_steps_after_the_version_it_was_made_at(self) -> None:
        upgrades = self._upgrades()
        self.assertEqual(upgrades.flow(Flow("a", "A"), 0).description, "123")
        self.assertEqual(upgrades.flow(Flow("a", "A"), 2).description, "3")
        with self.assertRaisesRegex(ValueError, "newer toolbox"):
            upgrades.flow(Flow("a", "A"), 4)

    def test_a_missing_step_is_a_mistake(self) -> None:
        with self.assertRaises(ValueError):
            SettingsUpgrades(self.config, [FakeSettingsUpgrade(1, self.ran), FakeSettingsUpgrade(3, self.ran)])


if __name__ == "__main__":
    unittest.main()
