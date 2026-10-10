import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.files.box_value_files import BoxValueFiles


class TestBoxValueFiles(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.files = BoxValueFiles(self.folder)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_save_list_load_per_kind(self) -> None:
        self.assertEqual(self.files.names("vts_animation"), [])
        self.files.save("vts_animation", "hop", {"steps": [1]})
        self.files.save("vts_animation", "Big shake", {"steps": [2]})
        self.assertTrue((self.folder / "vts_animation" / "hop.json").is_file())
        self.assertEqual(self.files.names("vts_animation"), ["Big_shake", "hop"])
        self.assertEqual(self.files.load("vts_animation", "hop"), {"steps": [1]})
        self.assertEqual(self.files.names("other"), [])

    def test_missing_and_bad_names(self) -> None:
        with self.assertRaises(KeyError):
            self.files.load("vts_animation", "nope")
        for bad in ("", "../x", "a/b", "c:"):
            with self.assertRaises(ValueError):
                self.files.save("vts_animation", bad, {})
