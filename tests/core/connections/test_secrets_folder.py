import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from streamer_toolbox.core.connections.secrets_folder import SecretsFolder


class TestSecretsFolder(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.settings = Path(self._dir.name) / "config"
        self.settings.mkdir()

    def test_a_new_secret_goes_into_the_sub_folder_which_is_made_only_when_needed(self) -> None:
        path = SecretsFolder(self.settings).path("thing_token.txt")

        self.assertEqual(self.settings / "secrets" / "thing_token.txt", path)
        self.assertFalse((self.settings / "secrets").exists())

    def test_the_first_secret_written_makes_the_folder_the_owners_only(self) -> None:
        path = SecretsFolder(self.settings).path("thing_token.txt")
        path.parent.mkdir()  # as a connection does before it writes: with the usual rights

        path.write_text("abc", encoding="utf-8")

        self.assertEqual("abc", path.read_text(encoding="utf-8"))
        if os.name == "posix":
            self.assertEqual(0o700, stat.S_IMODE(path.parent.stat().st_mode))

    def test_a_file_from_the_old_place_is_moved_over_once(self) -> None:
        (self.settings / "thing_token.txt").write_text("abc\n", encoding="utf-8")
        secrets = SecretsFolder(self.settings)

        path = secrets.path("thing_token.txt")

        self.assertEqual("abc\n", path.read_text(encoding="utf-8"))
        self.assertEqual(self.settings / "secrets", path.parent)
        self.assertFalse((self.settings / "thing_token.txt").exists())
        self.assertEqual(path, secrets.path("thing_token.txt"))

    def test_the_new_place_wins_and_the_old_file_is_left_alone(self) -> None:
        (self.settings / "secrets").mkdir()
        (self.settings / "secrets" / "thing_token.txt").write_text("new", encoding="utf-8")
        (self.settings / "thing_token.txt").write_text("old", encoding="utf-8")

        path = SecretsFolder(self.settings).path("thing_token.txt")

        self.assertEqual("new", path.read_text(encoding="utf-8"))
        self.assertEqual("old", (self.settings / "thing_token.txt").read_text(encoding="utf-8"))

    def test_a_failed_move_keeps_the_old_place_working(self) -> None:
        old = self.settings / "thing_token.txt"
        old.write_text("abc", encoding="utf-8")

        with mock.patch.object(Path, "replace", side_effect=PermissionError("in use")), \
                self.assertLogs("streamer_toolbox.core.connections.secrets_folder", "WARNING"):
            path = SecretsFolder(self.settings).path("thing_token.txt")

        self.assertEqual(old, path)
        self.assertEqual("abc", old.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
