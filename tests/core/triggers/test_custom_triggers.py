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
from streamer_toolbox.core.triggers.custom_trigger import CUSTOM
from streamer_toolbox.core.triggers.custom_trigger_actions import CustomTriggerActions
from streamer_toolbox.core.triggers.custom_trigger_router import CustomTriggerRouter
from streamer_toolbox.core.triggers.custom_trigger_store import CustomTriggerStore
from streamer_toolbox.core.variables.variable_store import VariableStore

REDEEM = FlowTrigger("twitch.redeem", {"reward": "Lizard", "reward_id": "r1"})
COMMAND = FlowTrigger("twitch.chat", {"command": "!lizard"})


class TestCustomTriggers(unittest.IsolatedAsyncioTestCase):
    """His round-18 idea: platforms fire a named trigger, one flow listens to it."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name)
        self.store = CustomTriggerStore(folder / "custom_triggers.json")
        self.actions = ActionRegistry()
        self.calls: list[dict] = []

        async def record(**params):
            self.calls.append(params)

        self.actions.add("a.record", record)
        runner = FlowRunner(self.actions, VariableStore(folder / "v.json"))
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "t"), runner, self.actions)
        self.flows.save(Flow("lizard", "Lizard", (FlowNode("n1", "a.record", {
            "who": "${event.user}", "from": "${event.platform}", "via": "${event.source}"}),),
            (FlowWire("start", "out", "n1"),), (FlowTrigger(CUSTOM, {"trigger": "lizard"}),)))
        self.bus = EventBus()
        self.bus.subscribe(FlowTriggerRouter(self.flows, runner).handle)
        self.bus.subscribe(CustomTriggerRouter(self.store, self.bus).handle)
        CustomTriggerActions(self.store, self.bus).add_to(self.actions)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_any_source_fires_it_and_the_one_flow_runs_with_the_platform(self) -> None:
        self.store.add("lizard", "a lizard on screen")
        self.store.add_source("lizard", REDEEM)
        self.store.add_source("lizard", COMMAND)
        self.bus.publish("twitch.redeem", {"reward": "Lizard (renamed)", "reward_id": "r1", "user": "VexFan",
                                           "platform": "twitch"})
        self.bus.publish("twitch.chat", {"command": "!lizard", "user": "Kit", "platform": "twitch"})
        self.bus.publish("twitch.chat", {"command": "!other", "user": "Nope", "platform": "twitch"})
        await self.bus.wait_idle()
        self.assertCountEqual(self.calls, [{"who": "VexFan", "from": "twitch", "via": "twitch.redeem"},
                                           {"who": "Kit", "from": "twitch", "via": "twitch.chat"}])

    async def test_fire_action_from_sammi_or_a_flow(self) -> None:
        self.store.add("Lizard")
        self.assertEqual(await self.actions.run("trigger.fire", trigger="lizard", platform="youtube", user="Yu"),
                         "Lizard")
        await self.bus.wait_idle()
        self.assertEqual(self.calls, [{"who": "Yu", "from": "youtube", "via": "trigger.fire"}])
        with self.assertRaises(KeyError):
            await self.actions.run("trigger.fire", trigger="nope")

    def test_store_keeps_names_unique_and_survives_a_restart(self) -> None:
        self.store.add("lizard")
        with self.assertRaises(ValueError):
            self.store.add("LIZARD")
        self.store.add_source("lizard", REDEEM)
        self.store.add_source("lizard", REDEEM)  # once is enough
        again = CustomTriggerStore(Path(self.tmp.name) / "custom_triggers.json")
        self.assertEqual(again.get("Lizard").sources, (REDEEM,))
        again.remove_source("lizard", REDEEM)
        self.assertEqual(again.get("lizard").sources, ())

    def test_renaming_moves_the_flows_along(self) -> None:
        self.assertEqual(self.flows.rename_custom_trigger("LIZARD", "mini lizard"), ["lizard"])
        self.assertEqual(self.flows.get("lizard").triggers[0].match, {"trigger": "mini lizard"})
