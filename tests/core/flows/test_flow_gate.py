import asyncio
import unittest

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_gate import FlowGate
from streamer_toolbox.core.flows.flow_skipped import FlowSkipped


class TestFlowGate(unittest.IsolatedAsyncioTestCase):
    async def _start_twice(self, when_busy: str) -> list[str]:
        """Two starts of one flow, the second while the first still runs; what happened, in order."""
        gate, flow, log = FlowGate(), Flow("redeem", "Redeem", when_busy=when_busy), []
        a_started, release = asyncio.Event(), asyncio.Event()  # no sleeps: the order can't depend on the PC's load

        async def run(name: str) -> None:
            try:
                async with gate.enter(flow):
                    log.append(f"{name} start")
                    a_started.set()
                    await release.wait()
                    log.append(f"{name} end")
            except FlowSkipped:
                log.append(f"{name} skipped")

        first = asyncio.create_task(run("a"))
        await a_started.wait()
        second = asyncio.create_task(run("b"))
        for _ in range(5):  # let b get as far as it can (running, in line, or skipped)
            await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, second)
        self.assertFalse(gate.is_running("redeem"))
        return log

    async def test_alongside(self) -> None:
        self.assertEqual(await self._start_twice("alongside"), ["a start", "b start", "a end", "b end"])

    async def test_queue(self) -> None:
        self.assertEqual(await self._start_twice("queue"), ["a start", "a end", "b start", "b end"])

    async def test_skip(self) -> None:
        self.assertEqual(await self._start_twice("skip"), ["a start", "b skipped", "a end"])


if __name__ == "__main__":
    unittest.main()
