import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.split_actions import SplitActions
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.media.video_actions import VideoActions
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import BY_NAME
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft
from streamer_toolbox.gui.components.flow_editor.node_editor import NodeEditor
from tests.fakes.fake_video_probe import FakeVideoProbe


class TestNodeEditorDataDots(unittest.TestCase):
    """Round 12: a box has one orange result dot; Split takes the keys of the box wired in by itself."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        actions = ActionRegistry()
        VideoActions(FakeVideoProbe({})).add_to(actions)
        SplitActions().add_to(actions)
        actions.add("a.name", _name)
        actions.add("a.send", _send, shown={"address": ("way", ("mail",)), "number": ("way", ("phone",))})
        variables = VariableStore(Path(self._dir.name) / "variables.json")
        self.draft = FlowDraft("f", "F", nodes=[
            NodeDraft("n1", "video.info", {"path": "clip.mp4"}),
            NodeDraft("n2", "data.split", {"data": "${box.n1}"}),
            NodeDraft("n3", "a.name", {})], triggers=[FlowTrigger("twitch.chat", {})])
        self.editor = NodeEditor(actions, FlowRunner(actions, variables), variables,
                                 BoxValueFiles(Path(self._dir.name) / "box_values"), self.draft, lambda **_: None)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_result_with_keys_has_one_dot_and_its_keys_stay_in_the_list(self) -> None:
        video = self.draft.node("n1")
        self.assertEqual(self.editor.data_outputs(video), [("", "result")])
        sources = self.editor.wire_sources(self.draft.node("n2"))
        self.assertIn("${box.n1}", sources)
        self.assertIn("${box.n1.width}", sources)

    def test_the_box_line_leaves_out_what_the_chosen_way_does_not_use(self) -> None:
        node = NodeDraft("n9", "a.send", {"address": "a@b.c", "number": "123"})
        self.assertEqual(self.editor.summary(node), "address = a@b.c")
        node.params["way"] = "phone"
        self.assertEqual(self.editor.summary(node), "number = 123, way = phone")

    def test_helpers_are_only_offered_where_they_fit(self) -> None:
        sources = self.editor.wire_sources(self.draft.node("n2"))
        helpers = {ref for ref in sources if ".@" in ref}
        self.assertEqual({r for r in helpers if r.startswith("${box.n1.")},  # an object: no @first, no @kind
                         {"${box.n1.@keys}", "${box.n1.@kinds}", "${box.n1.@count}", "${box.n1.@text}"})
        self.assertIn("${box.n3}", sources)
        self.assertEqual({r for r in helpers if r.startswith("${box.n3.")}, set())  # one text: nothing to pick
        self.assertIn("${box.start.message}", sources)
        self.assertEqual({r for r in helpers if r.startswith("${box.start.")}, set())

    def test_a_box_with_fields_gets_a_by_name_dot_first(self) -> None:
        video = self.draft.node("n1")
        video.params["path"] = "${box}"
        self.assertEqual(self.editor.data_inputs(video), [BY_NAME, "path"])
        self.assertNotIn(BY_NAME, self.editor.data_inputs(self.draft.node("n2")))  # Split: data is a dot already

    def test_split_takes_the_keys_of_the_box_wired_in(self) -> None:
        split = self.draft.node("n2")
        self.assertTrue(self.editor.fields_from_wire(split))
        self.assertEqual(split.params["fields"],
                         {"width": "number", "height": "number", "seconds": "number", "orientation": "text"})
        self.assertEqual([f for f, _ in self.editor.data_outputs(split)], ["width", "height", "seconds", "orientation"])

    def test_split_after_a_field_has_no_known_keys(self) -> None:
        split = self.draft.node("n2")
        split.params["data"] = "${box.n1.width}"
        self.assertFalse(self.editor.fields_from_wire(split))


async def _name() -> str:
    return "Dragon"


async def _send(way: str = "mail", address: str = "", number: str = "") -> None:
    pass


if __name__ == "__main__":
    unittest.main()
