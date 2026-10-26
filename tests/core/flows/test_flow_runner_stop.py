import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_stopped import FlowStopped
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestFlowRunnerStop(unittest.IsolatedAsyncioTestCase):
    """His round 63: an endless loop is stopped by hand, without restarting the toolbox."""

    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        actions = ActionRegistry()

        async def forever():
            while True:
                yield "each"
                await asyncio.sleep(0)

        async def loop():
            return forever()

        async def nothing():
            return None

        actions.add("a.loop", loop, ports=("each", "done"))
        actions.add("a.nothing", nothing)
        self.runner = FlowRunner(actions, VariableStore(Path(self.tmp.name) / "v.json"))
        self.flow = Flow("loop_test", "Loop test", (FlowNode("n1", "a.loop"), FlowNode("n2", "a.nothing")),
                         (FlowWire("start", "out", "n1"), FlowWire("n1", "each", "n2")))

    async def asyncTearDown(self) -> None:
        self.tmp.cleanup()

    async def _going(self, run) -> asyncio.Task:
        task = asyncio.create_task(run)
        for _ in range(20):
            await asyncio.sleep(0)
        return task

    async def test_stop_ends_an_endless_loop(self) -> None:
        task = await self._going(self.runner.run(self.flow))
        self.assertEqual((self.runner.running("loop_test"), self.runner.running("other")), (1, 0))
        self.assertEqual(self.runner.stop("loop_test"), 1)
        with self.assertRaises(FlowStopped):
            await task
        self.assertEqual(self.runner.running(), 0)

    async def test_a_test_run_stopped_says_so(self) -> None:
        task = await self._going(self.runner.test_run(self.flow))
        self.assertEqual(self.runner.stop(), 1)  # every flow
        results, error = await task
        self.assertIsInstance(error, FlowStopped)

    async def test_nothing_running_stops_nothing(self) -> None:
        self.assertEqual(self.runner.stop("loop_test"), 0)


if __name__ == "__main__":
    unittest.main()
