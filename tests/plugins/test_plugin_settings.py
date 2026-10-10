import json
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.plugins.plugin_settings import PluginSettings


class TestPluginSettings(unittest.TestCase):
    def test_defaults_from_resources_his_changes_in_config_on_top(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            defaults, saved = Path(tmp, "resources", "settings.json"), Path(tmp, "config", "plugins", "x.json")
            defaults.parent.mkdir()
            defaults.write_text(json.dumps({"size": 130, "hide": ["<-"]}), encoding="utf-8")
            settings = PluginSettings(defaults, saved)
            self.assertEqual(settings.load(), {"size": 130, "hide": ["<-"]})
            settings.save({"size": 200})
            settings.save({"last": "sounds"})
            self.assertEqual(settings.load(), {"size": 200, "hide": ["<-"], "last": "sounds"})
            self.assertEqual(json.loads(defaults.read_text(encoding="utf-8"))["size"], 130)  # defaults untouched
            saved.write_text("{broken", encoding="utf-8")
            with self.assertLogs(level="ERROR"):
                self.assertEqual(settings.load(), {"size": 130, "hide": ["<-"]})
            self.assertEqual(PluginSettings(None, Path(tmp, "none.json")).load(), {})
