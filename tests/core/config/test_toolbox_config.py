import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.config.toolbox_config import DEFAULT_CALLERS, ToolboxConfig
from streamer_toolbox.core.layout.box import Box

EXAMPLE = Path(__file__).resolve().parents[3] / "config" / "toolbox.example.toml"


class TestToolboxConfig(unittest.TestCase):
    def test_missing_file_gives_localhost_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ToolboxConfig.read(Path(tmp) / "toolbox.toml")
        self.assertEqual((config.host, config.port), ("127.0.0.1", 8850))
        self.assertIsNone(config.plugins_enabled)
        self.assertEqual(config.callers, DEFAULT_CALLERS)
        self.assertFalse(config.obs.enabled)

    def test_example_file_parses(self) -> None:
        config = ToolboxConfig.read(EXAMPLE)
        self.assertEqual(config.plugins_enabled, frozenset({"hello"}))
        self.assertEqual([c.name for c in config.callers], ["sammi", "kit"])
        self.assertFalse(config.obs.enabled)  # every connection is off until switched on
        self.assertEqual(config.tables["mixitup"]["url"], "http://localhost:8911/api/v2")
        raid = config.obs.fit_targets[0]
        self.assertEqual((raid.name, raid.source, raid.landscape),
                         ("raid_clip", "raid_video_clip", Box(0, 0, 576, 324)))

    def test_caller_needs_token_or_local(self) -> None:
        with self.assertRaisesRegex(ValueError, "token or local"):
            ToolboxConfig.parse({"callers": {"kit": {"allow": ["*"]}}})

    def test_short_token_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "too short"):
            ToolboxConfig.parse({"callers": {"kit": {"token": "abc", "allow": ["*"]}}})


if __name__ == "__main__":
    unittest.main()
