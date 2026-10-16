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
        self.assertEqual(self.files.names("vts/animation"), [])
        self.files.save("vts/animation", "hop", {"steps": [1]})
        self.files.save("vts/animation", "Big shake", {"steps": [2]})
        self.assertTrue((self.folder / "vts" / "animation" / "hop.json").is_file())
        self.assertEqual(self.files.names("vts/animation"), ["Big_shake", "hop"])
        self.assertEqual(self.files.load("vts/animation", "hop"), {"steps": [1]})
        self.assertEqual(self.files.names("other"), [])

    def test_missing_and_bad_names(self) -> None:
        with self.assertRaises(KeyError):
            self.files.load("vts/animation", "nope")
        for bad in ("", "../x", "a/b", "c:"):
            with self.assertRaises(ValueError):
                self.files.save("vts/animation", bad, {})
        for bad in ("", "../x", "vts/..", "/vts", "c:/x"):
            with self.assertRaises(ValueError):
                self.files.save(bad, "hop", {})
