import tempfile
import unittest
from pathlib import Path
from unittest import mock

from streamer_toolbox.core.files.move_once import move_once


class MoveOnceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.old = self.folder / "vts_positions.toml"
        self.new = self.folder / "boxes" / "vts" / "position" / "positions.toml"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_the_old_file_is_moved_the_first_time(self) -> None:
        self.old.write_text("spots", encoding="utf-8")
        self.assertEqual(move_once(self.old, self.new), self.new)
        self.assertEqual(self.new.read_text(encoding="utf-8"), "spots")
        self.assertFalse(self.old.exists())

    def test_a_folder_moves_with_what_is_in_it(self) -> None:
        old, new = self.folder / "box_values" / "vts_animation", self.folder / "boxes" / "vts" / "animation"
        old.mkdir(parents=True)
        (old / "wave.json").write_text("{}", encoding="utf-8")
        self.assertEqual(move_once(old, new), new)
        self.assertEqual([p.name for p in new.iterdir()], ["wave.json"])

    def test_nothing_old_or_something_new_already_changes_nothing(self) -> None:
        self.assertEqual(move_once(self.old, self.new), self.new)
        self.assertFalse(self.new.exists())
        self.new.parent.mkdir(parents=True)
        self.new.write_text("new", encoding="utf-8")
        self.old.write_text("old", encoding="utf-8")
        self.assertEqual(move_once(self.old, self.new), self.new)
        self.assertEqual((self.new.read_text(encoding="utf-8"), self.old.read_text(encoding="utf-8")), ("new", "old"))

    def test_what_cannot_be_moved_stays_and_is_used(self) -> None:
        self.old.write_text("spots", encoding="utf-8")
        with mock.patch.object(Path, "rename", side_effect=PermissionError("open")):
            self.assertEqual(move_once(self.old, self.new), self.old)
        self.assertEqual(self.old.read_text(encoding="utf-8"), "spots")
