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


class TestFlowRunnerLinesIn(unittest.IsolatedAsyncioTestCase):
    """Boxes with a run dot per line (Choose value, End): the line a wire comes in at is the one that's read
    (his round 53)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        variables = VariableStore(Path(self.tmp.name) / "variables.json")
        self.calls: list[dict] = []
        self.actions = ActionRegistry()

        async def record(**params):
            self.calls.append(params)
            return "ok"

        async def scene() -> str:
            return "desktop"

        self.actions.add("a.record", record)
        self.actions.add("a.scene", scene)
        LogicActions(variables).add_to(self.actions)
        self.runner = FlowRunner(self.actions, variables)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _choose(self, left: str, wire_2: FlowWire | None = None) -> Flow:
        """temp_test's way: the scene is checked, then and else go into Choose value's lines, the next box gets
        the value of the side that ran."""
        nodes = (FlowNode("s", "a.scene"), FlowNode("if", "logic.if", {"left": left, "right": "${box.s}"}),
                 FlowNode("c", "logic.choose", {"values": 2, "value_1": "Just_chatting", "value_2": "${box.s}"}),
                 FlowNode("r", "a.record", {"scene": "${box.c}"}))
        wires = (FlowWire("start", "out", "s"), FlowWire("s", "done", "if"),
                 FlowWire("if", "then", "c", "value_1"), wire_2 or FlowWire("if", "else", "c", "value_2"),
                 FlowWire("c", "done", "r"))
        return Flow("f", "F", nodes, wires)

    async def test_the_value_of_the_line_that_ran_goes_on(self) -> None:
        await self.runner.run(self._choose("desktop"))
        await self.runner.run(self._choose("game"))
        self.assertEqual(self.calls, [{"scene": "Just_chatting"}, {"scene": "desktop"}])

    async def test_a_wire_into_the_normal_run_dot_counts_as_the_first_line(self) -> None:
        await self.runner.run(self._choose("game", FlowWire("if", "else", "c")))
        self.assertEqual(self.calls, [{"scene": "Just_chatting"}])

    async def test_the_other_lines_are_not_read(self) -> None:
        nodes = (FlowNode("never", "a.record", {"never": 1}),
                 FlowNode("c", "logic.choose", {"value_1": "5", "value_2": "${box.never}"}),
                 FlowNode("r", "a.record", {"n": "${box.c}"}))
        wires = (FlowWire("start", "out", "c", "value_1"), FlowWire("c", "done", "r"))
        await self.runner.run(Flow("f", "F", nodes, wires))
        self.assertEqual(self.calls, [{"n": 5}])  # a typed line is read like Value's: 5 is a number

    async def test_one_end_box_with_two_names_gives_the_flow_box_two_outputs(self) -> None:
        nodes = (FlowNode("ask", "logic.if", {"left": "${input.n}", "op": ">", "right": "5"}),
                 FlowNode("end", "logic.end", {"names": 2, "name_1": "big", "name_2": "small"}))
        inner = Flow("size", "Size", nodes, (FlowWire("start", "out", "ask"), FlowWire("ask", "then", "end", "name_1"),
                                              FlowWire("ask", "else", "end", "name_2")))
        self.assertEqual(inner.ends, ("big", "small"))
        self.runner.register(inner)
        outer_nodes = (FlowNode("s", "flow.size", {"n": "${input.n}"}), FlowNode("b", "a.record", {"was": "big"}),
                       FlowNode("m", "a.record", {"was": "small"}))
        outer = Flow("outer", "Outer", outer_nodes,
                     (FlowWire("start", "out", "s"), FlowWire("s", "big", "b"), FlowWire("s", "small", "m")))
        await self.runner.run(outer, inputs={"n": "9"})
        await self.runner.run(outer, inputs={"n": "2"})
        self.assertEqual(self.calls, [{"was": "big"}, {"was": "small"}])

    async def test_a_box_with_lines_gives_what_it_gave_when_it_ran(self) -> None:
        nodes = (FlowNode("c", "logic.choose", {"value_1": "a", "value_2": "b"}),
                 FlowNode("r", "a.record", {"got": "${box.c}"}))
        wires = (FlowWire("start", "out", "c", "value_2"), FlowWire("start", "out", "r"))
        _, error = await self.runner.test_run(Flow("f", "F", nodes, wires))
        self.assertIn("hasn't run yet", str(error))  # it runs in the flow, so it isn't run for the data wire
