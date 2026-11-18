import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestFlowRunnerOutputsHeard(unittest.IsolatedAsyncioTestCase):
    """His 11-18: a Live button follows an output of its flow, from every run of it (DeckStates listens)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.actions = ActionRegistry()
        LogicActions(VariableStore(Path(self.tmp.name) / "variables.json")).add_to(self.actions)
        self.runner = FlowRunner(self.actions, VariableStore(Path(self.tmp.name) / "v2.json"))
        self.heard: list[tuple[str, dict]] = []
        self.runner.outputs_heard.append(lambda flow, outputs: self.heard.append((flow, outputs)))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_end_box_and_flow_output_box_are_heard(self) -> None:
        nodes = (FlowNode("o", "logic.output", {"name": "active", "value": "${input.on}"}),
                 FlowNode("end", "logic.end", {"mode": "loud"}))
        flow = Flow("mic", "Mic", nodes, (FlowWire("start", "out", "o"), FlowWire("o", "done", "end")))
        await self.runner.run(flow, inputs={"on": True})
        self.assertEqual(self.heard, [("mic", {"active": True}), ("mic", {"mode": "loud"})])

    async def test_a_started_flow_box_is_heard_too_and_a_box_test_is_not(self) -> None:
        flow = Flow("mic", "Mic", (FlowNode("end", "logic.end", {"active": "false"}),),
                    (FlowWire("start", "out", "end"),))
        self.runner.register(flow)
        await self.actions.run("flow.mic")  # a Live press runs it like this
        self.assertEqual(self.heard, [("mic", {"active": False})])
        await self.runner.run_node(flow, flow.node("end"))  # the editor's Test of one box
        self.assertEqual(len(self.heard), 1)
