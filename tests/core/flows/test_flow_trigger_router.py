import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_trigger_router import FlowTriggerRouter
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestFlowTriggerRouter(unittest.IsolatedAsyncioTestCase):
    async def test_a_redeem_runs_the_matching_flows_with_the_event_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            actions = ActionRegistry()
            calls, reports = [], []

            async def record(**params):
                calls.append(params)

            async def boom():
                raise ValueError("no")

            actions.add("a.record", record)
            actions.add("a.boom", boom)
            runner = FlowRunner(actions, VariableStore(folder / "v.json"))
            library = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "t"), runner, actions)
            wire = (FlowWire("start", "out", "n1"),)
            trigger = (FlowTrigger("twitch.redeem", {"reward": "Big Action: clean screen"}),)
            library.save(Flow("wipe", "Wipe", (FlowNode("n1", "a.record", {"by": "${event.user}"}),), wire, trigger))
            library.save(Flow("broken", "Broken", (FlowNode("n1", "a.boom"),), wire, trigger))
            library.save(Flow("other", "Other", (FlowNode("n1", "a.record", {"by": "wrong"}),), wire,
                              (FlowTrigger("twitch.redeem", {"reward": "Hydrate"}),)))
            bus = EventBus()
            bus.subscribe(FlowTriggerRouter(library, runner, lambda *entry: reports.append(entry)).handle)
            bus.publish("twitch.redeem", {"reward": "big action: clean SCREEN", "user": "VexFan"})
            await bus.wait_idle()
        self.assertEqual(calls, [{"by": "VexFan"}])
        self.assertEqual(sorted((r[1], r[2]) for r in reports), [("flow.broken", False), ("flow.wipe", True)])

    async def test_cooldown_and_refund(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            actions, refunds, reports = ActionRegistry(), [], []

            async def boom():
                raise ValueError("board offline")

            async def ok():
                return "ok"

            async def refund(data):
                refunds.append(data["redemption_id"])

            actions.add("a.boom", boom)
            actions.add("a.ok", ok)
            runner = FlowRunner(actions, VariableStore(folder / "v.json"))
            library = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "t"), runner, actions)
            wire = (FlowWire("start", "out", "n1"),)
            library.save(Flow("board", "Board", (FlowNode("n1", "a.boom"),), wire,
                              (FlowTrigger("twitch.redeem", {"reward": "Board"}),), refund_on_fail=True))
            library.save(Flow("hi", "Hi", (FlowNode("n1", "a.ok"),), wire,
                              (FlowTrigger("twitch.chat", {"command": "!hi"}),), user_cooldown=60))
            router = FlowTriggerRouter(library, runner, lambda *entry: reports.append(entry), refund)
            await router.handle("twitch.redeem", {"reward": "Board", "redemption_id": "red1"})
            for user in ("kit", "Kit", "vex"):
                await router.handle("twitch.chat", {"command": "!hi", "user_login": user})
        self.assertEqual(refunds, ["red1"])
        held = [r[3] for r in reports if r[1] == "flow.hi"]
        self.assertEqual((held[0], held[2]), ("1 boxes", "1 boxes"))
        self.assertIn("cooldown", held[1])  # kit again, within a minute


if __name__ == "__main__":
    unittest.main()
