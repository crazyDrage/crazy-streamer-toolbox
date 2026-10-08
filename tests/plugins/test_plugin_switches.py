import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.gui.components.flow_editor.trigger_kinds import TRIGGER_KINDS, offered_triggers
from streamer_toolbox.plugins.plugin_switches import PluginSwitches


class TestPluginSwitches(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "config" / "plugins_off.json"
        self.switches = PluginSwitches(self.path)

    def test_every_plugin_is_on_until_switched_off_and_it_is_kept(self) -> None:
        self.assertEqual(self.switches.off(), set())
        self.switches.switch("lamp", on=False)
        self.switches.switch("decks", on=False)
        self.assertEqual(PluginSwitches(self.path).off(), {"lamp", "decks"})
        self.switches.switch("lamp", on=True)
        self.switches.switch("never_off", on=True)
        self.assertEqual(PluginSwitches(self.path).off(), {"decks"})

    def test_a_file_that_cannot_be_read_means_everything_is_on(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.switches.off(), set())
        self.path.write_text('{"lamp": true}', encoding="utf-8")
        self.assertEqual(self.switches.off(), set())

    def test_the_triggers_of_a_plugin_that_is_off_are_not_offered(self) -> None:
        TRIGGER_KINDS["lamp.blinked"] = ("lightbulb", "Lamp blinked", "color", "*")
        self.addCleanup(TRIGGER_KINDS.pop, "lamp.blinked")
        self.assertIn("lamp.blinked", offered_triggers(lambda: {}))
        self.switches.switch("lamp", on=False)
        self.assertNotIn("lamp.blinked", offered_triggers(lambda: {pid: pid for pid in self.switches.off()}))


if __name__ == "__main__":
    unittest.main()
