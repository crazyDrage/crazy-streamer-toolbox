import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.connections.secret_file import SecretFile


class TestSecretFile(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "thing_token.txt"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_missing_or_empty_file_is_said_with_where_the_secret_comes_from(self) -> None:
        secret = SecretFile(self.path, "token", "Thing → Settings")
        self.assertEqual(secret.read_or_empty(), "")
        with self.assertRaisesRegex(ValueError, r"No token yet: type the token \(Thing → Settings\) into its field"):
            secret.read()
        self.path.write_text("  \n", encoding="utf-8")
        with self.assertRaises(ValueError):
            SecretFile(self.path, "token").read()
        self.assertEqual(secret.hide("nothing to hide"), "nothing to hide")

    def test_the_first_line_is_the_secret_and_it_is_taken_out_of_texts(self) -> None:
        self.path.write_text("\n  abc123  \nsomething else\n", encoding="utf-8")
        secret = SecretFile(self.path, "API key")
        self.assertEqual(secret.read(), "abc123")
        self.assertEqual(secret.hide("failed at ws://x?token=abc123"), "failed at ws://x?token=<API key>")

    def test_the_tabs_field_writes_it_and_an_empty_one_takes_it_away(self) -> None:
        secret = SecretFile(self.path.parent / "new" / "thing_token.txt", "token")
        secret.write("  pasted-with-spaces \nand a second line")
        self.assertEqual((secret.read(), secret.path.read_text(encoding="utf-8")),
                         ("pasted-with-spaces", "pasted-with-spaces\n"))
        secret.write("  ")
        self.assertEqual(secret.read_or_empty(), "")


if __name__ == "__main__":
    unittest.main()
