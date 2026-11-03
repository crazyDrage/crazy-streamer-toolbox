import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.object_actions import ObjectActions
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.box_dots import BoxDots
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft
from streamer_toolbox.gui.components.flow_editor.node_draft import NodeDraft

POSITION = '{"x": -0.2, "y": 0.1, "model": "Dragon"}'


async def _raw() -> dict:
    return {}


class TestBoxOwnOutputs(unittest.TestCase):
    """His round 60: Object values has a dot per key of what's wired in; any box can keep dots of its own."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        actions = ActionRegistry()
        variables = VariableStore(Path(self._dir.name) / "variables.json")
        LogicActions(variables).add_to(actions)
        ObjectActions().add_to(actions)
        actions.add("obs.raw", _raw)
        self.runner = FlowRunner(actions, variables)
        self.draft = FlowDraft("f", "F", nodes=[
            NodeDraft("n1", "logic.value", {"values": {"model_pos": POSITION}}),
            NodeDraft("n2", "object.values", {"object": "${box.n1.model_pos}"}),
            NodeDraft("n3", "obs.raw", {})])
        self.dots = BoxDots(actions, self.runner, self.draft)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_object_values_has_a_dot_per_key_of_a_wired_value_line(self) -> None:
        values = self.draft.node("n2")
        self.assertEqual(self.dots.data_outputs(values), [
            ("", "result"), ("x", "x · number"), ("y", "y · number"), ("model", "model · text")])
        self.assertEqual(self.dots.output_kind("n2", "model"), "text")
        self.assertIn("${box.n2.x}", self.dots.wire_sources(NodeDraft("n9", "object.values", {})))

    def test_the_keys_follow_the_wire_and_stay_when_nothing_is_known(self) -> None:
        values = self.draft.node("n2")
        self.dots.data_outputs(values)
        values.params["object"] = "${box.n3}"  # never ran: what it had stays
        self.assertEqual(list(self.dots.own_outputs(values)), ["x", "y", "model"])
        self.runner._last[("f", "n3")] = {"sceneName": "Intro"}
        self.assertEqual(self.dots.own_outputs(values), {"sceneName": "text"})

    def test_a_box_keeps_its_own_dots_in_the_flow_file(self) -> None:
        raw = self.draft.node("n3")
        raw.outputs = {"inputSettings": "object"}
        self.assertEqual(self.dots.data_outputs(raw), [("", "result"), ("inputSettings", "inputSettings · object")])
        store = FlowStore(Path(self._dir.name) / "flows")
        store.save(self.draft.to_flow())
        node = next(f for f in store.all() if f.name == "f").node("n3")
        self.assertEqual(node, FlowNode("n3", "obs.raw", outputs={"inputSettings": "object"}))
        self.assertEqual(NodeDraft.from_node(node).outputs, {"inputSettings": "object"})


if __name__ == "__main__":
    unittest.main()
