import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.flows.default_flows import DefaultFlows
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.variables.variable_store import VariableStore

PACK = """
toolbox_flows = 1
folder = "Test flows"

[[flows]]
name = "thank"
label = "Thank a follow"
wires = [{from = "follow", port = "out", to = "n1"}]

[[flows.triggers]]
kind = "twitch.follow"
id = "follow"

[[flows.nodes]]
id = "n1"
action = "a.record"
params = {text = "${box.follow.user}"}

[[flows]]
name = "raid"
label = "Thank a raid"
"""


class TestDefaultFlows(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name)
        actions = ActionRegistry()
        self.library = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "flow_templates"),
                                   FlowRunner(actions, VariableStore(folder / "variables.json")), actions)
        self.file = folder / "default.flows.toml"
        self.file.write_text(PACK, encoding="utf-8")
        self.defaults = DefaultFlows(self.library)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_they_come_in_switched_off_in_the_files_folder(self) -> None:
        added, there = self.defaults.add(self.file)
        self.assertEqual((added, there), (["Thank a follow", "Thank a raid"], []))
        flow = self.library.get("thank")
        self.assertEqual((flow.enabled, flow.folder, len(flow.triggers)), (False, "Test flows", 1))

    def test_pressing_again_brings_back_only_the_missing_ones(self) -> None:
        self.defaults.add(self.file)
        self.library.save(Flow("thank", "Thank a follow", description="his own words", folder="Test flows"))
        self.library.delete("raid")
        added, there = self.defaults.add(self.file)
        self.assertEqual((added, there), (["Thank a raid"], ["Thank a follow"]))
        self.assertEqual(self.library.get("thank").description, "his own words")

    def test_a_taken_label_elsewhere_keeps_its_label_and_trigger(self) -> None:
        self.library.save(Flow("mine", "Thank a follow", folder="Mine"))
        self.defaults.add(self.file)
        theirs = next(f for f in self.library.all() if f.folder == "Test flows" and f.label == "Thank a follow")
        self.assertEqual(len(theirs.triggers), 1)
        self.assertNotEqual(theirs.name, "mine")

    def test_only_the_picked_ones_come_in(self) -> None:
        added, there = self.defaults.add(self.file, only={"Thank a raid"})
        self.assertEqual((added, there), (["Thank a raid"], []))
        self.assertEqual([f.label for f in self.library.all()], ["Thank a raid"])

    def test_there_names_the_ones_in_the_folder(self) -> None:
        self.assertEqual(self.defaults.there(self.file), set())
        self.defaults.add(self.file, only={"Thank a follow"})
        self.assertEqual(self.defaults.there(self.file), {"thank a follow"})

    def test_another_folder_can_be_named(self) -> None:
        self.defaults.add(self.file, "Examples")
        self.assertEqual({f.folder for f in self.library.all()}, {"Examples"})

    def test_the_live_deck_stays_as_it_was(self) -> None:
        self.library.save(Flow("mine", "Mine"))
        deck = DeckStore(Path(self.tmp.name) / "live_deck.json", self.library.all)
        DefaultFlows(self.library, deck).add(self.file)
        actions = [b.action for page in deck.load().pages for b in page.buttons]
        self.assertEqual(["flow.mine"], actions)  # his round 88: no Live button for the default flows


if __name__ == "__main__":
    unittest.main()
