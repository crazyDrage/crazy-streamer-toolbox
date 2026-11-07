import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from streamer_toolbox.core.system.update_swap import UpdateSwap, swap


class TestUpdateSwap(unittest.TestCase):
    """His next release plan, part 1: the new version goes in, his settings stay."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        base = Path(self._dir.name)
        self.into, self.new, self.old = base / "toolbox", base / "new", base / "update" / "old"
        for folder, version in ((self.into, "old"), (self.new, "new")):
            self.write(folder / "src" / "streamer_toolbox" / "__init__.py", version)
            self.write(folder / "python" / "python.exe", version)
            self.write(folder / "plugins" / "example" / "main.py", version)
            self.write(folder / "README.md", version)
        self.write(self.into / "src" / "streamer_toolbox" / "gone.py", "old")
        self.write(self.into / "config" / "toolbox.toml", "his settings")
        self.write(self.into / "plugins" / "his_own" / "main.py", "his plugin")
        self.write(self.new / "config" / "toolbox.example.toml", "not copied")  # config/ is never touched

    def tearDown(self) -> None:
        self._dir.cleanup()

    @staticmethod
    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read(self, *parts: str) -> str:
        return self.into.joinpath(*parts).read_text(encoding="utf-8")

    def test_the_new_files_go_in_and_his_stay(self) -> None:
        UpdateSwap(self.new, self.into, self.old).run()
        self.assertEqual(self.read("src", "streamer_toolbox", "__init__.py"), "new")
        self.assertFalse((self.into / "src" / "streamer_toolbox" / "gone.py").exists())  # src/ replaced whole
        self.assertEqual((self.read("python", "python.exe"), self.read("README.md")), ("new", "new"))
        self.assertEqual(self.read("plugins", "example", "main.py"), "new")
        self.assertEqual(self.read("plugins", "his_own", "main.py"), "his plugin")
        self.assertEqual(self.read("config", "toolbox.toml"), "his settings")
        self.assertFalse((self.into / "config" / "toolbox.example.toml").exists())

    def test_a_file_in_use_is_tried_again(self) -> None:
        real = __import__("shutil").copy2
        busy = [PermissionError("in use"), PermissionError("in use")]

        def copy(source, target):
            if Path(source).name == "README.md" and busy:
                raise busy.pop()
            return real(source, target)

        with mock.patch("streamer_toolbox.core.system.update_swap.shutil.copy2", copy):
            UpdateSwap(self.new, self.into, self.old, sleep=lambda s: None).run()
        self.assertEqual(self.read("README.md"), "new")

    def test_when_it_fails_the_old_version_stays(self) -> None:
        with mock.patch("streamer_toolbox.core.system.update_swap.shutil.copy2", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                UpdateSwap(self.new, self.into, self.old).run()
        self.assertEqual(self.read("src", "streamer_toolbox", "__init__.py"), "old")
        self.assertEqual(self.read("src", "streamer_toolbox", "gone.py"), "old")
        self.assertEqual(self.read("python", "python.exe"), "old")

    def test_the_swap_says_what_the_update_window_shows_and_writes_the_result(self) -> None:
        folder = self.old.parent
        with mock.patch("streamer_toolbox.core.system.update_swap.start_again") as started:
            said = swap(self.new, self.into, folder, "0.4.0", ["python", "-m", "streamer_toolbox"])
        self.assertIn("Version 0.4.0 is starting", said)
        self.assertTrue(json.loads((folder / "result.json").read_text())["ok"])
        started.assert_called_once()


if __name__ == "__main__":
    unittest.main()
