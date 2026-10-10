import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.plugins.plugin_manifest import PluginManifest

GOOD = {"id": "lamp", "name": "Lamp", "version": "0.1", "api_version": 1}


class TestPluginManifest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "plugin.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _read(self, data) -> PluginManifest:
        self.path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return PluginManifest.read(self.path)

    def test_valid_manifest_with_defaults(self) -> None:
        m = self._read({**GOOD, "description": "a lamp"})
        self.assertEqual((m.id, m.api_version, m.main, m.class_name, m.description, m.folder),
                         ("lamp", 1, "main.py", "", "a lamp", self.path.parent))
        self.assertEqual(m.resources, self.path.parent / "resources")

    def test_missing_fields_are_named(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing name, version"):
            self._read({"id": "lamp", "api_version": 1})

    def test_id_must_be_a_safe_package_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "id must be"):
            self._read({**GOOD, "id": "../evil"})

    def test_main_and_class_are_checked(self) -> None:
        with self.assertRaisesRegex(ValueError, "main must be"):
            self._read({**GOOD, "main": "../x.py"})
        with self.assertRaisesRegex(ValueError, "class must be"):
            self._read({**GOOD, "class": "a b"})

    def test_bad_json_is_explained(self) -> None:
        with self.assertRaisesRegex(ValueError, "not valid JSON"):
            self._read("{id: lamp")


if __name__ == "__main__":
    unittest.main()
