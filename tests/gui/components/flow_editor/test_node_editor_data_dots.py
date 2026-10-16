import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.media.video_actions import VideoActions
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.drawflow_graph import BY_NAME
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft
from streamer_toolbox.gui.components.flow_editor.node_editor import NodeEditor
from tests.fakes.fake_video_probe import FakeVideoProbe


class TestNodeEditorDataDots(unittest.TestCase):
    """Round 12: a box has one orange result dot, and one per key it is known to give."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        actions = ActionRegistry()
        VideoActions(FakeVideoProbe({})).add_to(actions)
        actions.add("a.name", _name)
        actions.add("a.take", _take)
        actions.add("a.send", _send, shown={"address": ("way", ("mail",)), "number": ("way", ("phone",))})
        variables = VariableStore(Path(self._dir.name) / "variables.json")
        LogicActions(variables).add_to(actions)
        self.draft = FlowDraft("f", "F", nodes=[
            NodeDraft("n1", "video.info", {"path": "clip.mp4"}),
            NodeDraft("n2", "a.take", {"data": "${box.n1}"}),
            NodeDraft("n3", "a.name", {})], triggers=[FlowTrigger("twitch.chat", {})])
        self.editor = NodeEditor(actions, FlowRunner(actions, variables), variables,
                                 BoxValueFiles(Path(self._dir.name) / "box_values"), self.draft, lambda **_: None)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_a_wire_taken_away_in_the_panel_is_set_after_the_canvas_was_read(self) -> None:
        split, calls = self.draft.node("n2"), []
        self.editor._on_change = lambda **how: calls.append(how)
        self.editor._set_param(split, "data", "${box}")  # the X on "from box"
        self.assertEqual((split.params["data"], calls[0]["rebuild"]), ("${box.n1}", True))  # not yet
        calls[0]["edit"]()  # the box view runs it once it has read the canvas, which still shows the old wire
        self.assertEqual(split.params["data"], "${box}")
        self.editor._set_param(split, "data", "5")  # another source: nothing on the canvas puts a wire back
        self.assertEqual((split.params["data"], calls[1]), ("5", {"rebuild": False}))

    def test_a_result_with_keys_has_a_dot_for_itself_and_one_per_key(self) -> None:
        video = self.draft.node("n1")
        self.assertEqual(self.editor.dots.data_outputs(video), [
            ("", "result"), ("width", "width · number"), ("height", "height · number"),
            ("seconds", "seconds · number"), ("orientation", "orientation · text")])
        sources = self.editor.dots.wire_sources(self.draft.node("n2"))
        self.assertIn("${box.n1}", sources)
        self.assertIn("${box.n1.width}", sources)

    def test_every_field_is_a_dot_wired_or_not(self) -> None:
        self.assertEqual(self.editor.dots.data_inputs(self.draft.node("n1")), [BY_NAME, "path"])
        self.draft.node("n2").params["data"] = ""
        self.assertEqual(self.editor.dots.data_inputs(self.draft.node("n2")), [BY_NAME, "data"])
        send = NodeDraft("n9", "a.send", {})
        self.assertEqual(self.editor.dots.data_inputs(send), [BY_NAME, "way", "address"])  # way is "mail" at first
        send.params.update(way="phone", address="${box.n3}")  # a wired one stays, also when the way hides it
        self.assertEqual(self.editor.dots.data_inputs(send), [BY_NAME, "way", "address", "number"])

    def test_start_gives_what_the_triggers_give_and_then_the_flow_inputs(self) -> None:
        self.draft.inputs = [FlowInput("video"), FlowInput("message")]
        outputs = self.editor.dots.start_outputs()
        self.assertEqual(outputs[-2:], [("video", "video (input)"), ("message", "message (input)")])
        self.assertIn(("user", "user"), outputs[:-2])
        self.assertNotIn(("message", "message"), outputs)  # an input of that name is the one dot

    def test_the_box_line_leaves_out_what_the_chosen_way_does_not_use(self) -> None:
        node = NodeDraft("n9", "a.send", {"address": "a@b.c", "number": "123"})
        self.assertEqual(self.editor.dots.summary(node), "address = a@b.c")
        node.params["way"] = "phone"
        self.assertEqual(self.editor.dots.summary(node), "number = 123, way = phone")

    def test_helpers_are_only_offered_where_they_fit(self) -> None:
        sources = self.editor.dots.wire_sources(self.draft.node("n2"))
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
        self.assertEqual(self.editor.dots.data_inputs(video), [BY_NAME, "path"])

    def test_a_value_box_has_a_dot_per_line_and_no_field_dots(self) -> None:
        value = NodeDraft("n8", "logic.value", {"values": {"power": "10", "model": "Hex", "who": "${var.x}"}})
        self.assertEqual(self.editor.dots.data_outputs(value),
                         [("power", "power · number"), ("model", "model · text"), ("who", "who")])
        self.assertEqual(self.editor.dots.data_inputs(value), [])


async def _take(data: object) -> None:
    pass


async def _name() -> str:
    return "Dragon"


async def _send(way: str = "mail", address: str = "", number: str = "") -> None:
    pass


if __name__ == "__main__":
    unittest.main()
