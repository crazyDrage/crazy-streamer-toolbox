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


class TestFlowRunnerSwitch(unittest.IsolatedAsyncioTestCase):
    """A Switch with as many cases as it has: each case its own output, then else."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        variables = VariableStore(Path(self.tmp.name) / "variables.json")
        self.went: list[str] = []
        actions = ActionRegistry()

        async def mark(name: str) -> None:
            self.went.append(name)

        actions.add("a.mark", mark)
        LogicActions(variables).add_to(actions)
        self.runner = FlowRunner(actions, variables)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def _run(self, value: str) -> list[str]:
        self.went.clear()
        cases = {"cases": 6, "case_1": "ra, right_arm", "case_2": "la", "case_5": "tail"}  # 3, 4, 6 are empty
        nodes = (FlowNode("sw", "logic.switch", {"value": value, **cases}),
                 *(FlowNode(port, "a.mark", {"name": port}) for port in ("case_1", "case_5", "case_6", "else")))
        wires = (FlowWire("start", "out", "sw"),
                 *(FlowWire("sw", port, port) for port in ("case_1", "case_5", "case_6", "else")))
        await self.runner.run(Flow("f", "F", nodes, wires))
        return self.went

    async def test_goes_through_the_case_that_matches(self) -> None:
        self.assertEqual(await self._run("Right_Arm"), ["case_1"])
        self.assertEqual(await self._run("tail"), ["case_5"])

    async def test_empty_cases_never_match_and_the_rest_goes_to_else(self) -> None:
        self.assertEqual(await self._run(""), ["else"])
        self.assertEqual(await self._run("head"), ["else"])


if __name__ == "__main__":
    unittest.main()
