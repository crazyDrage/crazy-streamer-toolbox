import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.connections.inbox_types import InboxTypes


class TestInboxTypes(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.file = Path(self._dir.name) / "inbox_types.json"
        self.types = InboxTypes(self.file)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_each_connection_keeps_its_own_types_once(self) -> None:
        self.types.add("warudo", "default")
        self.types.add("warudo", "camera")
        self.types.add("warudo", "camera")
        self.types.add("other", "x")
        self.assertEqual(["camera", "default"], InboxTypes(self.file).known("warudo"))
        self.assertEqual(["x"], self.types.known("other"))
        self.types.remove("warudo", "camera")
        self.types.remove("warudo", "never there")
        self.assertEqual(["default"], self.types.known("warudo"))

    def test_a_missing_or_broken_file_is_no_types(self) -> None:
        self.assertEqual([], self.types.known("warudo"))
        self.file.write_text("{broken", encoding="utf-8")
        self.assertEqual([], self.types.known("warudo"))
        self.types.add("warudo", "default")
        self.assertEqual(["default"], self.types.known("warudo"))


if __name__ == "__main__":
    unittest.main()
