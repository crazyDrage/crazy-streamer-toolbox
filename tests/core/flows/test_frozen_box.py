import asyncio
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.frozen_box import FrozenBox
from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.flow_draft import FlowDraft

POSITION = {"x": 0.12, "y": -0.4, "rotation": 0, "size": -38}


class MoveModel(Box):
    name = "move"
    freeze = None  # gives no answer: nothing to keep

    async def run(self) -> None:
        return None


class TestFrozenBox(unittest.TestCase):
    """His idea of 10-29: freeze a box, it gives what it saved and doesn't run; kept in the flow's file."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.folder = Path(self._dir.name)
        self.asked = 0
        self.seen: list = []
        self.actions = ActionRegistry()

        async def position() -> dict:
            self.asked += 1
            return dict(POSITION)

        async def record(x: float = 0) -> None:
            self.seen.append(x)

        self.actions.add("vts.position", position)
        self.actions.add("t.record", record)
        self.actions.add_box(MoveModel(), "vts")
        self.flow = Flow("f", "F", (FlowNode("n1", "vts.position"), FlowNode("n2", "t.record", {"x": "${box.n1.x}"})),
                         (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _frozen(self) -> Flow:
        draft = FlowDraft.from_flow(self.flow)
        draft.freeze("n1", dict(POSITION), "2026-10-29 21:14")
        return draft.to_flow()

    def test_a_frozen_box_gives_what_it_saved_and_doesnt_run(self) -> None:
        frozen = self._frozen()
        self.assertEqual(frozen.wires, (FlowWire("start", "out", "n2"),))  # the chain goes round it
        runner = FlowRunner(self.actions, VariableStore(self.folder / "v.json"))
        runner.register(frozen)
        asyncio.run(self.actions.run("flow.f"))
        self.assertEqual((self.seen, self.asked), ([0.12], 0))  # VTube Studio wasn't asked

    def test_it_is_kept_in_the_flows_file(self) -> None:
        store = FlowStore(self.folder / "flows")
        store.save(self._frozen())
        node = store.read("f").node("n1")
        self.assertEqual((node.frozen.value, node.frozen.at), (POSITION, "2026-10-29 21:14"))
        self.assertEqual(node.frozen.wires, (FlowWire("start", "out", "n1"), FlowWire("n1", "done", "n2")))
        nothing = replace(node, frozen=FrozenBox(None, "x"))  # a box that gave nothing stays "nothing"
        store.save(replace(store.read("f"), nodes=(nothing, *store.read("f").nodes[1:])))
        self.assertIsNone(store.read("f").node("n1").frozen.value)

    def test_unfreeze_brings_its_wires_back(self) -> None:
        draft = FlowDraft.from_flow(self._frozen())
        draft.unfreeze("n1")
        self.assertEqual(sorted(draft.wires, key=str), sorted(self.flow.wires, key=str))
        self.assertIsNone(draft.node("n1").frozen)

    def test_run_again_keeps_its_hidden_wires(self) -> None:
        draft = FlowDraft.from_flow(self._frozen())
        draft.freeze("n1", {"x": 1}, "2026-10-30 10:00")
        self.assertEqual((draft.node("n1").frozen.value, len(draft.node("n1").frozen.wires)), ({"x": 1}, 2))

    def test_which_boxes_can_be_frozen(self) -> None:
        self.assertTrue(self.actions.get("vts.position").freezable)
        self.assertFalse(self.actions.get("vts.move").freezable)  # freeze = None
        self.actions.add("t.if", self.actions.get("t.record").handler, ports=("then", "else"))
        self.assertFalse(self.actions.get("t.if").freezable)  # it steers the flow
        self.assertFalse(self.actions.get("t.record").freezable)  # -> None: it gives no answer, said or not


if __name__ == "__main__":
    unittest.main()
