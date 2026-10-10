import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import STRETCHED, FlowRunner
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.flows.logic_actions import LogicActions
from streamer_toolbox.core.variables.variable_store import VariableStore

WAIT = 0.2


class TestFlowRunnerRetrigger(unittest.IsolatedAsyncioTestCase):
    """Light on, Wait, light off: starting the flow again during the wait stretches it instead of running twice."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        variables = VariableStore(Path(self.tmp.name) / "variables.json")
        self.log: list[tuple[str, float]] = []
        actions = ActionRegistry()

        async def light(state: str) -> None:
            self.log.append((state, asyncio.get_running_loop().time()))

        actions.add("a.light", light)
        LogicActions(variables).add_to(actions)
        self.runner = FlowRunner(actions, variables)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _flow(if_started_again: str, when_busy: str = "alongside") -> Flow:
        nodes = (FlowNode("on", "a.light", {"state": "on"}),
                 FlowNode("wait", "logic.wait", {"seconds": WAIT, "if_started_again": if_started_again}),
                 FlowNode("off", "a.light", {"state": "off"}))
        wires = (FlowWire("start", "out", "on"), FlowWire("on", "done", "wait"), FlowWire("wait", "done", "off"))
        return Flow("light", "Light", nodes, wires, when_busy=when_busy)

    async def _start_at(self, flow: Flow, *delays: float) -> list[list[dict]]:
        async def later(delay: float) -> list[dict]:
            await asyncio.sleep(delay)
            return await self.runner.run(flow)

        return await asyncio.gather(*(later(d) for d in delays))

    def _on_for(self) -> float:
        (on, start), (off, end) = self.log
        self.assertEqual((on, off), ("on", "off"))
        return end - start

    async def test_start_over_keeps_it_on_for_the_whole_time_after_the_last_start(self) -> None:
        first, second = await self._start_at(self._flow("restart"), 0, WAIT / 2)
        self.assertEqual(second, [STRETCHED])
        self.assertEqual(next(r["result"] for r in first if r["box"] == "wait"), 1)
        self.assertGreaterEqual(self._on_for(), WAIT * 1.5 - 0.02)

    async def test_add_time_adds_the_seconds_once_per_start(self) -> None:
        await self._start_at(self._flow("add"), 0, WAIT / 4, WAIT / 2)
        self.assertGreaterEqual(self._on_for(), WAIT * 3 - 0.02)

    async def test_also_works_for_a_flow_that_waits_in_line_or_skips(self) -> None:
        for when_busy in ("queue", "skip"):
            self.log.clear()
            _, second = await self._start_at(self._flow("restart", when_busy), 0, WAIT / 2)
            self.assertEqual(second, [STRETCHED])
            self.assertGreaterEqual(self._on_for(), WAIT * 1.5 - 0.02)

    async def test_a_start_after_the_wait_runs_again(self) -> None:
        flow = self._flow("restart")
        flow = Flow(flow.name, flow.label, flow.nodes + (FlowNode("slow", "logic.wait", {"seconds": WAIT}),),
                    flow.wires + (FlowWire("off", "done", "slow"),))
        _, second = await self._start_at(flow, 0, WAIT * 1.5)  # the first run is in its plain wait by then
        self.assertNotEqual(second, [STRETCHED])
        self.assertEqual([state for state, _ in self.log], ["on", "off", "on", "off"])

    async def test_nothing_runs_alongside_as_before(self) -> None:
        _, second = await self._start_at(self._flow("nothing"), 0, WAIT / 2)
        self.assertNotEqual(second, [STRETCHED])
        self.assertEqual([state for state, _ in self.log], ["on", "on", "off", "off"])

    async def test_a_test_run_is_a_plain_wait(self) -> None:
        results, error = await self.runner.test_run(self._flow("restart"))
        self.assertIsNone(error)
        self.assertEqual(next(r["result"] for r in results if r["box"] == "wait"), 0)


if __name__ == "__main__":
    unittest.main()
