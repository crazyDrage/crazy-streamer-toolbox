import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.timer_clock import TimerClock
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestTimerClock(unittest.IsolatedAsyncioTestCase):
    async def test_publishes_each_interval_when_due_without_bursts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            actions = ActionRegistry()
            library = FlowLibrary(FlowStore(folder / "f"), FlowStore(folder / "t"),
                                  FlowRunner(actions, VariableStore(folder / "v.json")), actions)
            library.save(Flow("tick", "Tick", triggers=(FlowTrigger("timer", {"every": "1"}),)))
            library.save(Flow("slow", "Slow", triggers=(FlowTrigger("timer", {"every": "2.5"}),)))
            library.save(Flow("bad", "Bad", triggers=(FlowTrigger("timer", {"every": "soon"}),)))
            bus, seen = EventBus(), []

            async def record(kind, data):
                seen.append(data["every"])

            bus.subscribe(record)
            clock = TimerClock(library, bus)
            ticks = {}
            for now in (100.0, 100.5, 101.0, 102.0, 102.5, 110.0, 110.1, 111.0):
                clock.check(now)
                await bus.wait_idle()
                ticks[now] = sorted(seen)
                seen.clear()
        self.assertEqual(ticks, {100.0: [], 100.5: [], 101.0: ["1"], 102.0: ["1"], 102.5: ["2.5"],
                                 110.0: ["1", "2.5"], 110.1: [], 111.0: ["1"]})


if __name__ == "__main__":
    unittest.main()
