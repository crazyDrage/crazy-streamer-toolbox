import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.widgets.design_files import DesignFiles
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class DesignFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.store = WidgetStore(Path(self.folder.name))
        self.store.save(Widget("bar"))
        self.files = DesignFiles(self.store)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def test_a_name_the_folder_takes(self) -> None:
        self.assertEqual("my_cat_dance.gif", self.files.add("bar", "my cat (dance).GIF", b"gif"))
        self.assertEqual(b"gif", self.store.media_file("bar", "my_cat_dance.gif").read_bytes())

    def test_the_same_file_again_is_used_again(self) -> None:
        self.assertEqual("a.png", self.files.add("bar", "a.png", b"one"))
        self.assertEqual("a.png", self.files.add("bar", "a.png", b"one"))
        self.assertEqual("a_2.png", self.files.add("bar", "a.png", b"two"))
        self.assertEqual("a_3.png", self.files.add("bar", "a.png", b"three"))

    def test_no_widget_no_file(self) -> None:
        with self.assertRaises(KeyError):
            self.files.add("gone", "a.png", b"one")


if __name__ == "__main__":
    unittest.main()
