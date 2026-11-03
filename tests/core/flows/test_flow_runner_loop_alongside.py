import asyncio
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


class TestFlowRunnerLoopAlongside(unittest.IsolatedAsyncioTestCase):
    """His round 63: a Loop is one per flow (a timer that only gets longer) or one per start (each redeem throws
    its own items on the model)."""

    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        variables = VariableStore(Path(self.tmp.name) / "v", Path(self.tmp.name) / "v.json")
        self.actions = ActionRegistry()
        LogicActions(variables).add_to(self.actions)
        self.thrown = []

        async def throw(who: str, round: int):
            self.thrown.append((who, round))

        self.actions.add("a.throw", throw)
        self.runner = FlowRunner(self.actions, variables)

    async def asyncTearDown(self) -> None:
        self.tmp.cleanup()

    def _flow(self, mode: str, rounds: int = 3, stop_at: int = 0) -> Flow:
        nodes = [FlowNode("loop", "logic.loop", {"rounds": rounds, "pause": 0.05, "if_already_looping": mode}),
                 FlowNode("throw", "a.throw", {"who": "${box.input.who}", "round": "${box.loop.round}"})]
        wires = [FlowWire("start", "out", "loop"), FlowWire("loop", "each", "throw")]
        if stop_at:  # a run stops its own loop at that round
            nodes.append(FlowNode("check", "logic.if", {"left": "${box.loop.round}", "op": "==", "right": stop_at}))
            wires += [FlowWire("throw", "done", "check"), FlowWire("check", "then", "loop", "stop")]
        return Flow("tits", "TITS", tuple(nodes), tuple(wires))

    async def _two_starts(self, flow: Flow) -> list[list[dict]]:
        first = asyncio.create_task(self.runner.run(flow, inputs={"who": "a"}))
        await asyncio.sleep(0.02)
        return [*await asyncio.gather(first, self.runner.run(flow, inputs={"who": "b"}))]

    async def test_only_one_loop_a_second_start_stops_there(self) -> None:
        _, second = await self._two_starts(self._flow("one"))
        self.assertEqual(second[-1]["result"], "already running")
        self.assertEqual(self.thrown, [("a", 1), ("a", 2), ("a", 3)])

    async def test_alongside_every_start_loops_on_its_own(self) -> None:
        await self._two_starts(self._flow("alongside"))
        self.assertEqual(sorted(self.thrown), [("a", 1), ("a", 2), ("a", 3), ("b", 1), ("b", 2), ("b", 3)])

    async def test_alongside_a_run_stops_its_own_loop(self) -> None:
        await self._two_starts(self._flow("alongside", rounds=0, stop_at=2))  # a stops while b still loops
        self.assertEqual(sorted(self.thrown), [("a", 1), ("a", 2), ("b", 1), ("b", 2)])


if __name__ == "__main__":
    unittest.main()
