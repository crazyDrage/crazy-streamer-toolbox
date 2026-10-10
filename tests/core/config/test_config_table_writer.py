import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.config.toolbox_config import ToolboxConfig

EXAMPLE = Path(__file__).resolve().parents[3] / "config" / "toolbox.example.toml"


class TestConfigTableWriter(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "config" / "toolbox.toml"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_creates_file_with_only_that_table(self) -> None:
        ConfigTableWriter(self.path).save("obs", {"enabled": True, "url": "ws://127.0.0.1:4455", "password": "pw"})
        config = ToolboxConfig.read(self.path)
        self.assertEqual((config.obs.enabled, config.obs.url, config.obs.password),
                         (True, "ws://127.0.0.1:4455", "pw"))
        self.assertEqual(config.callers, ToolboxConfig().callers)

    def test_keeps_comments_other_tables_and_fit_targets(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        ConfigTableWriter(self.path).save("obs", {"enabled": True, "url": "ws://127.0.0.1:4456"})
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("# Who may call the HTTP API.", text)
        config = ToolboxConfig.read(self.path)
        self.assertEqual((config.obs.enabled, config.obs.url), (True, "ws://127.0.0.1:4456"))
        self.assertEqual([t.name for t in config.obs.fit_targets], ["raid_clip", "sound_alert"])
        self.assertEqual(config.plugins_enabled, frozenset({"hello"}))

    def test_none_keeps_the_saved_value(self) -> None:
        writer = ConfigTableWriter(self.path)
        writer.save("sammi", {"url": "http://a", "password": "pw"})
        writer.save("sammi", {"url": "http://b", "password": None})
        self.assertEqual(ToolboxConfig.read(self.path).tables["sammi"], {"url": "http://b", "password": "pw"})


if __name__ == "__main__":
    unittest.main()
