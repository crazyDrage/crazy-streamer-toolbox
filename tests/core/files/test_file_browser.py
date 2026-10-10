import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.files.file_browser import FileBrowser
from streamer_toolbox.core.files.file_types import FOLDER, VIDEO_TYPES


class TestFileBrowser(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.home = Path(self._dir.name)
        (self.home / "Videos" / "raids").mkdir(parents=True)
        for name in ("boom.MP4", "alpha.mov", "notes.txt"):
            (self.home / "Videos" / name).write_text("")
        self.browser = FileBrowser(self.home)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_lists_folders_and_the_files_that_fit(self) -> None:
        listing = self.browser.listing(self.home / "Videos", VIDEO_TYPES)
        self.assertEqual((listing.folders, listing.files), (("raids",), ("alpha.mov", "boom.MP4")))
        self.assertEqual(listing.parent, self.home)
        self.assertEqual(self.browser.listing(self.home / "Videos").files, ("alpha.mov", "boom.MP4", "notes.txt"))
        self.assertEqual(self.browser.listing(self.home / "Videos", FOLDER).files, ())

    def test_a_folder_that_cant_be_read_says_why(self) -> None:
        listing = self.browser.listing(self.home / "gone")
        self.assertEqual((listing.folders, listing.files, listing.problem), ((), (), "this folder isn't there"))
        self.assertIn("a file, not a folder", self.browser.listing(self.home / "Videos" / "notes.txt").problem)

    def test_opens_where_the_value_is_else_the_last_folder_else_home(self) -> None:
        videos = self.home / "Videos"
        self.assertEqual(self.browser.start(str(videos / "boom.MP4")), videos)
        self.assertEqual(self.browser.start(str(videos / "new.png")), videos)  # a file that isn't there yet
        self.assertEqual(self.browser.start(str(videos)), videos)
        self.assertEqual(self.browser.start("${var.clip}", videos / "raids"), videos / "raids")
        self.assertEqual(self.browser.start("meme.ogg"), self.home)  # a name in the sound folder: no folder to show
        self.assertEqual(self.browser.start("", self.home / "gone"), self.home)

    def test_places_to_jump_to(self) -> None:
        places = self.browser.places()
        self.assertEqual(places[str(self.home)], "Home")
        self.assertEqual(places[str(self.home / "Videos")], "Videos")
        self.assertNotIn(str(self.home / "Music"), places)


if __name__ == "__main__":
    unittest.main()
