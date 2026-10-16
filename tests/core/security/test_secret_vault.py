import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.connections.secrets_folder import SecretsFolder
from streamer_toolbox.core.security.secret_vault import LOGIN_FILE, MARK, SecretVault

PASSWORD = "correct horse"


class TestSecretVault(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.settings = Path(self._dir.name) / "config"
        self.folder = self.settings / "secrets"
        self.folder.mkdir(parents=True)
        (self.folder / "thing_token.txt").write_bytes(b"abc123\n")

    def test_without_a_login_files_are_plain_and_nothing_is_locked(self) -> None:
        secrets = SecretsFolder(self.settings)
        token = secrets.path("thing_token.txt")

        token.write_text("new-token", encoding="utf-8")

        self.assertFalse(secrets.vault.active)
        self.assertTrue(secrets.vault.unlocked)
        self.assertEqual(b"new-token", (self.folder / "thing_token.txt").read_bytes())
        self.assertEqual("new-token", token.read_text(encoding="utf-8"))

    def test_a_login_encrypts_every_file_and_they_still_read_the_same(self) -> None:
        secrets = SecretsFolder(self.settings)
        token = secrets.path("thing_token.txt")

        secrets.vault.set_login(PASSWORD)
        token_on_disk = (self.folder / "thing_token.txt").read_bytes()
        secrets.path("other_key.txt").write_text("k-9", encoding="utf-8")

        self.assertTrue(token_on_disk.startswith(MARK))
        self.assertNotIn(b"abc123", token_on_disk)
        self.assertNotIn(b"k-9", (self.folder / "other_key.txt").read_bytes())
        self.assertEqual("abc123\n", token.read_text(encoding="utf-8"))
        self.assertEqual("k-9", secrets.path("other_key.txt").read_text(encoding="utf-8"))
        login = (self.folder / LOGIN_FILE).read_text(encoding="utf-8")
        self.assertNotIn(PASSWORD, login)

    def test_after_a_start_it_is_locked_until_the_right_password(self) -> None:
        SecretsFolder(self.settings).vault.set_login(PASSWORD)
        secrets = SecretsFolder(self.settings)  # a new start
        token = secrets.path("thing_token.txt")

        self.assertTrue(secrets.vault.active)
        self.assertFalse(secrets.vault.unlocked)
        self.assertEqual("", token.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(PermissionError, "log in first"):
            token.write_text("clobber", encoding="utf-8")
        self.assertFalse(secrets.vault.unlock("wrong horse"))
        self.assertFalse(secrets.vault.unlocked)

        self.assertTrue(secrets.vault.unlock(PASSWORD))
        self.assertEqual("abc123\n", token.read_text(encoding="utf-8"))

    def test_switching_it_off_makes_the_files_plain_again_and_needs_the_password(self) -> None:
        vault = SecretsFolder(self.settings).vault
        vault.set_login(PASSWORD)

        self.assertFalse(vault.remove_login("wrong horse"))
        self.assertTrue(vault.active)
        self.assertTrue(vault.remove_login(PASSWORD))

        self.assertFalse(vault.active)
        self.assertEqual(b"abc123\n", (self.folder / "thing_token.txt").read_bytes())
        self.assertEqual(["thing_token.txt"], [file.name for file in self.folder.iterdir()])

    def test_a_plain_file_next_to_a_login_is_read_as_it_is_and_encrypted_at_its_next_write(self) -> None:
        secrets = SecretsFolder(self.settings)
        secrets.vault.set_login(PASSWORD)
        (self.folder / "late_token.txt").write_text("plain", encoding="utf-8")
        late = secrets.path("late_token.txt")

        self.assertEqual("plain", late.read_text(encoding="utf-8"))
        late.write_text("plain", encoding="utf-8")

        self.assertTrue((self.folder / "late_token.txt").read_bytes().startswith(MARK))

    def test_an_old_file_is_moved_in_encrypted_when_a_login_is_set(self) -> None:
        secrets = SecretsFolder(self.settings)
        secrets.vault.set_login(PASSWORD)
        (self.settings / "old_token.txt").write_text("from-before", encoding="utf-8")

        moved = secrets.path("old_token.txt")

        self.assertFalse((self.settings / "old_token.txt").exists())
        self.assertTrue((self.folder / "old_token.txt").read_bytes().startswith(MARK))
        self.assertEqual("from-before", moved.read_text(encoding="utf-8"))

    def test_a_short_password_and_a_second_login_are_refused(self) -> None:
        vault = SecretVault(self.folder)
        with self.assertRaisesRegex(ValueError, "at least 8"):
            vault.set_login("short")
        vault.set_login(PASSWORD)
        with self.assertRaisesRegex(ValueError, "already set"):
            vault.set_login("another one")

    def test_a_secret_paths_relatives_are_plain_paths(self) -> None:
        token = SecretsFolder(self.settings).path("thing_token.txt")

        self.assertIs(type(token.parent), type(Path()))
        self.assertIs(type(token.with_name("x.tmp")), type(Path()))
        self.assertEqual(self.folder / "thing_token.txt", token)


if __name__ == "__main__":
    unittest.main()
