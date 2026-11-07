import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.connections.account_keys import AccountKeys, fit_name
from streamer_toolbox.core.upgrades.rumble_accounts_upgrade import RumbleAccountsUpgrade


class TestAccountKeys(unittest.TestCase):
    """Keys of a platform without a login (Rumble's address), one file per account (2026-11-06)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.secrets = Path(self.tmp.name)
        self.main = {"name": ""}
        folder = self.secrets / "rumble"
        self.keys = AccountKeys(folder, lambda file: folder / file, lambda: self.main["name"],
                                lambda name: self.main.update(name=name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_save_load_main_rename_remove(self) -> None:
        self.assertEqual(self.keys.save("Crazy Drage", " https://rumble.com/a \n"), "crazy_drage")
        self.keys.save("second", "https://rumble.com/b")
        self.assertEqual((self.keys.names(), self.keys.main_name()), (["crazy_drage", "second"], "crazy_drage"))
        self.assertEqual(self.keys.load("crazy_drage"), "https://rumble.com/a")
        self.assertEqual(self.keys.rename("crazy_drage", "drage"), "drage")
        self.assertEqual((self.keys.names(), self.main["name"]), (["drage", "second"], "drage"))
        self.keys.remove("drage")
        self.assertEqual(self.keys.main_name(), "second")  # the one left
        self.assertEqual(self.keys.load("../x"), "")  # never outside its folder

    def test_the_single_file_moves_once(self) -> None:
        old = self.secrets / "rumble_address.txt"
        old.write_text("https://rumble.com/a", encoding="utf-8")
        upgrade = RumbleAccountsUpgrade(lambda: self.keys.move_single_file(old, "rumble"))
        self.assertEqual(upgrade.run(), ["the Rumble address moved to secrets/rumble/rumble.txt, rumble is the "
                                         "main account"])
        self.assertFalse(old.exists())
        self.assertEqual((self.keys.names(), self.main["name"]), (["rumble"], "rumble"))
        self.assertEqual(upgrade.run(), [])  # twice changes nothing

    def test_names_fit(self) -> None:
        self.assertEqual(fit_name("@Crazy.Drage-2"), "crazy_drage_2")


if __name__ == "__main__":
    unittest.main()
