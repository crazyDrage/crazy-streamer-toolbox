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


class TestFlowRunnerEndValues(unittest.IsolatedAsyncioTestCase):
    """His rounds 54 and 55: the End box has one run dot and named values; the flow's box in another flow gets
    the values as orange dots, named like the End box's lines."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        variables = VariableStore(Path(self.tmp.name) / "variables.json")
        self.calls: list[dict] = []
        self.actions = ActionRegistry()

        async def record(**params):
            self.calls.append(params)

        async def scene() -> str:
            return "desktop"

        self.actions.add("a.record", record)
        self.actions.add("a.scene", scene)
        LogicActions(variables).add_to(self.actions)
        self.runner = FlowRunner(self.actions, variables)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _size() -> Flow:
        nodes = (FlowNode("sc", "a.scene"),
                 FlowNode("ask", "logic.if", {"left": "${input.n}", "op": ">", "right": "5"}),
                 FlowNode("big", "logic.choose", {"value_1": "big", "value_2": "small", "values": 2}),
                 FlowNode("end", "logic.end", {"size": "${box.big}", "scene": "${box.sc}", "count": "3"}))
        wires = (FlowWire("start", "out", "sc"), FlowWire("sc", "done", "ask"),
                 FlowWire("ask", "then", "big", "value_1"), FlowWire("ask", "else", "big", "value_2"),
                 FlowWire("big", "done", "end"))
        return Flow("size", "Size", nodes, wires)

    async def test_its_values_are_the_flow_boxes_named_outputs(self) -> None:
        inner = self._size()
        self.assertEqual(self.runner.outputs_of(inner), ("size", "scene", "count"))
        self.runner.register(inner)
        self.assertEqual(self.actions.get("flow.size").outputs, {"size": "", "scene": "", "count": ""})
        outer_nodes = (FlowNode("s", "flow.size", {"n": "${input.n}"}),
                       FlowNode("b", "a.record", {"size": "${box.s.size}", "scene": "${box.s.scene}",
                                                  "count": "${box.s.count}"}))
        outer = Flow("outer", "Outer", outer_nodes, (FlowWire("start", "out", "s"), FlowWire("s", "done", "b")))
        await self.runner.run(outer, inputs={"n": "9"})
        await self.runner.run(outer, inputs={"n": "2"})
        # a wired value keeps its kind, a typed one is read like a Value line (3 is a number)
        self.assertEqual(self.calls, [{"size": "big", "scene": "desktop", "count": 3},
                                      {"size": "small", "scene": "desktop", "count": 3}])

    def test_the_end_box_has_one_run_dot_and_a_data_dot_per_value(self) -> None:
        end = self.actions.get("logic.end")
        params = {"scene": "${box.sc}", "count": "3"}
        self.assertEqual((end.lines_named(params), end.entry_lines(params)), (["scene", "count"], []))


if __name__ == "__main__":
    unittest.main()
