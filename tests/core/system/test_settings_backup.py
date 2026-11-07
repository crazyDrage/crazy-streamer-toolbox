import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from streamer_toolbox.core.system.backup_policy import BackupPolicy
from streamer_toolbox.core.system.settings_backup import SettingsBackup
from streamer_toolbox.core.system.starter_settings import StarterSettings


class TestSettingsBackup(unittest.TestCase):
    """His round 84: the starter's backup of the settings folder, kept to the daily / monthly counts."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.settings = Path(self._dir.name)
        for name in ("toolbox.toml", "flows/a.toml", "cache/big.bin", "app_window/Local State", "secrets/t.txt"):
            (self.settings / name).parent.mkdir(parents=True, exist_ok=True)
            (self.settings / name).write_text("x", encoding="utf-8")

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_checked_zip_without_downloads_and_window_data(self) -> None:
        made = SettingsBackup(self.settings, lambda: time.mktime((2026, 11, 3, 21, 5, 9, 0, 0, -1))).make()
        self.assertEqual(made.name, "settings-2026-11-03_21-05-09.zip")
        with zipfile.ZipFile(made) as packed:
            self.assertEqual(sorted(packed.namelist()), ["flows/a.toml", "secrets/t.txt", "toolbox.toml"])
        self.assertTrue(SettingsBackup(self.settings).made_today())

    def test_prune_keeps_what_the_policy_says(self) -> None:
        backup = SettingsBackup(self.settings)
        backup.folder.mkdir()
        for number, day in enumerate((3, 2, 1), 1):
            zip_path = backup.folder / f"settings-{number}.zip"
            zip_path.write_bytes(b"")
            stamp = time.mktime((2026, 11, day, 12, 0, 0, 0, 0, -1))
            os.utime(zip_path, (stamp, stamp))
        gone = backup.prune(BackupPolicy(daily=2, monthly=0))
        self.assertEqual([p.name for p in gone], ["settings-3.zip"])
        self.assertEqual([p.name for p in backup.all()], ["settings-1.zip", "settings-2.zip"])

    def test_upgrade_backups_have_their_own_folder_the_starters_prune_leaves_alone(self) -> None:
        upgrade = SettingsBackup(self.settings, sub="upgrades").make("settings-v1-before-v2")
        self.assertEqual(upgrade.parent, self.settings / "backups" / "upgrades")
        starter = SettingsBackup(self.settings)
        starter.make()
        self.assertEqual(len(starter.all()), 1)  # only its own
        starter.prune(BackupPolicy(daily=0, monthly=0))
        self.assertTrue(upgrade.is_file())
        with zipfile.ZipFile(SettingsBackup(self.settings, sub="upgrades").make("again")) as packed:
            self.assertFalse(any(name.startswith("backups/") for name in packed.namelist()))

    def test_starter_settings_are_written_whole_and_read_back(self) -> None:
        self.assertEqual(StarterSettings.read(self.settings), StarterSettings())
        settings = StarterSettings(open_mode="lean-window", start_without_asking=True, daily=3, monthly=4)
        settings.write(self.settings)
        self.assertEqual(StarterSettings.read(self.settings), settings)
        self.assertFalse((self.settings / "starter.json.tmp").exists())
        (self.settings / "starter.json").write_text('{"open_mode": "weird", "daily": -2}', encoding="utf-8")
        read = StarterSettings.read(self.settings)
        self.assertEqual((read.open_mode, read.daily), ("window", 0))


if __name__ == "__main__":
    unittest.main()
