import tempfile
import unittest
from pathlib import Path
from unittest import mock

from streamer_toolbox.core.files import write_whole as module
from streamer_toolbox.core.files.write_whole import write_whole


class TestWriteWhole(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.file = self.folder / "data.json"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_writes_text_and_leaves_no_temp_file(self) -> None:
        write_whole(self.file, "äbc")
        self.assertEqual("äbc", self.file.read_text(encoding="utf-8"))
        self.assertEqual(["data.json"], [p.name for p in self.folder.iterdir()])

    def test_writes_bytes(self) -> None:
        write_whole(self.file, b"\x00\x01")
        self.assertEqual(b"\x00\x01", self.file.read_bytes())

    def test_replaces_an_old_file(self) -> None:
        self.file.write_text("old", encoding="utf-8")
        write_whole(self.file, "new")
        self.assertEqual("new", self.file.read_text(encoding="utf-8"))

    def test_a_failed_write_keeps_the_old_file(self) -> None:
        self.file.write_text("old", encoding="utf-8")
        with mock.patch.object(Path, "write_bytes", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                write_whole(self.file, "new")
        self.assertEqual("old", self.file.read_text(encoding="utf-8"))

    def test_held_open_file_is_tried_again(self) -> None:
        real = module.os.replace
        calls = []

        def busy_once(src, dst):
            calls.append(src)
            if len(calls) == 1:
                raise PermissionError("in use")
            real(src, dst)

        with mock.patch.object(module.os, "replace", side_effect=busy_once), mock.patch.object(module, "WAIT", 0):
            write_whole(self.file, "new")
        self.assertEqual(2, len(calls))
        self.assertEqual("new", self.file.read_text(encoding="utf-8"))

    def test_held_open_too_long_writes_straight_in(self) -> None:
        self.file.write_text("old", encoding="utf-8")
        with mock.patch.object(module.os, "replace", side_effect=PermissionError("in use")), \
                mock.patch.object(module, "WAIT", 0), self.assertLogs(module.log, "WARNING"):
            write_whole(self.file, "new")
        self.assertEqual("new", self.file.read_text(encoding="utf-8"))
        self.assertEqual(["data.json"], [p.name for p in self.folder.iterdir()])


if __name__ == "__main__":
    unittest.main()
