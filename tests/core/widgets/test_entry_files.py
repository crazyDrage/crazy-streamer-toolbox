import os
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.widgets.entry_files import EntryFiles


class TestEntryFiles(unittest.TestCase):
    def setUp(self) -> None:
        self._folder = tempfile.TemporaryDirectory()
        self.root = Path(self._folder.name)
        (self.root / "toolbox" / "pictures").mkdir(parents=True)
        (self.root / "toolbox" / "pictures" / "cat.gif").write_bytes(b"GIF")
        (self.root / "pics").mkdir()
        (self.root / "pics" / "fox.png").write_bytes(b"PNG")
        (self.root / "pics" / "notes.txt").write_text("private")
        (self.root / "secret.png").write_bytes(b"PNG")
        self.files = EntryFiles(self.root / "toolbox")
        self.pics = str(self.root / "pics")

    def tearDown(self) -> None:
        self._folder.cleanup()

    def test_a_path_its_address_makes_with_values(self):
        addresses = {self.pics + os.sep + "{user}.png"}  # this system's own separator (\ on Windows, / on Linux)
        self.assertEqual(self.root / "pics" / "fox.png", self.files.find(addresses, self.pics + os.sep + "fox.png"))

    def test_a_path_in_the_toolbox_folder(self):
        self.assertEqual(self.root / "toolbox" / "pictures" / "cat.gif",
                         self.files.find({"pictures/cat.gif"}, "pictures/cat.gif"))

    def test_a_value_is_never_a_folder_or_a_way_up(self):
        addresses = {self.pics + os.sep + "{user}.png"}
        self.assertIsNone(self.files.find(addresses, self.pics + "\\..\\secret.png"))
        self.assertIsNone(self.files.find(addresses, self.pics + "/../secret.png"))
        self.assertIsNone(self.files.find({"pictures/{message}"}, "pictures/../../secret.png"))

    def test_only_its_own_addresses_and_only_pictures_or_videos(self):
        self.assertIsNone(self.files.find(set(), self.pics + os.sep + "fox.png"))
        self.assertIsNone(self.files.find({self.pics + os.sep + "{user}.txt"}, self.pics + os.sep + "notes.txt"))
        self.assertIsNone(self.files.find({self.pics + os.sep + "{user}.png"}, self.pics + os.sep + "gone.png"))
        self.assertIsNone(self.files.find({"x"}, ""))


if __name__ == "__main__":
    unittest.main()
