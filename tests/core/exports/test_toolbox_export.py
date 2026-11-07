import io
import json
import unittest
import zipfile

from streamer_toolbox.core.exports.toolbox_export import ToolboxExport
from streamer_toolbox.core.upgrades.settings_version import SETTINGS_VERSION


class TestToolboxExport(unittest.TestCase):
    """The .toolbox file: a zip with manifest.json and the files."""

    def test_it_reads_back(self) -> None:
        made = ToolboxExport("Cheer", [{"kind": "event", "key": "cheer", "title": "cheer", "data": {"name": "cheer"},
                                        "files": {"/a.png": "files/1/a.png"}}], {"files/1/a.png": b"png"})
        read = ToolboxExport.from_bytes(made.to_bytes())
        self.assertEqual(("Cheer", made.entries, made.files, SETTINGS_VERSION),
                         (read.title, read.entries, read.files, read.settings_version))

    def test_other_files_are_refused_with_a_reason(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a zip"):
            ToolboxExport.from_bytes(b"hello")
        with self.assertRaisesRegex(ValueError, "no manifest"):
            ToolboxExport.from_bytes(self._zip({"a.txt": "x"}))
        with self.assertRaisesRegex(ValueError, "newer toolbox"):
            ToolboxExport.from_bytes(self._zip({"manifest.json": json.dumps({"toolbox_export": 99})}))

    def test_a_place_that_leads_out_of_the_folder_is_left_out(self) -> None:
        manifest = {"toolbox_export": 1, "parts": [{"kind": "flow", "key": "x", "files": {"a": "../evil.py"}}]}
        read = ToolboxExport.from_bytes(self._zip({"manifest.json": json.dumps(manifest), "../evil.py": "x"}))
        self.assertEqual({}, read.files)

    @staticmethod
    def _zip(files: dict[str, str]) -> bytes:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            for name, text in files.items():
                archive.writestr(name, text)
        return out.getvalue()


if __name__ == "__main__":
    unittest.main()
