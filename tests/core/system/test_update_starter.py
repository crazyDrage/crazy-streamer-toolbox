import json
import sys
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.system.toolbox_update import READY
from streamer_toolbox.core.system.update_starter import UpdateStarter


class TestUpdateStarter(unittest.TestCase):
    """In the launcher: the swap runs with the new toolbox's Python, so the old one can be replaced."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        base = Path(self._dir.name)
        self.folder, self.root, self.new = base / "update", base / "toolbox", base / "update" / "0.3.0" / "t"
        self.python = self.new / "python" / ("python.exe" if sys.platform == "win32" else "bin/python3")
        self.python.parent.mkdir(parents=True)
        self.python.write_bytes(b"")
        self.started: list[tuple[list[str], dict]] = []

    def tearDown(self) -> None:
        self._dir.cleanup()

    def starter(self) -> UpdateStarter:
        return UpdateStarter(self.folder, self.root, ["toolbox", "--open", "window"],
                             lambda command, **options: self.started.append((command, options)))

    def test_the_swap_is_started_with_the_new_python(self) -> None:
        (self.folder / READY).write_text(json.dumps({"version": "0.3.0", "new": str(self.new)}), encoding="utf-8")
        self.assertTrue(self.starter().start())
        command, options = self.started[0]
        self.assertEqual(command[:3], [str(self.python), "-m", "streamer_toolbox.core.system.update_swap"])
        self.assertEqual(command[command.index("--"):], ["--", "toolbox", "--open", "window"])
        self.assertEqual((options["cwd"], options["env"]["PYTHONPATH"]), (self.new, str(self.new / "src")))
        self.assertFalse((self.folder / READY).exists())

    def test_without_an_update_ready_the_old_toolbox_starts_again(self) -> None:
        self.assertFalse(self.starter().start())
        (self.folder / READY).write_text(json.dumps({"version": "0.3.0", "new": str(self.root)}), encoding="utf-8")
        self.assertFalse(self.starter().start())  # no Python in it
        self.assertEqual(self.started, [])


if __name__ == "__main__":
    unittest.main()
