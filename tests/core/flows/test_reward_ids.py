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
from streamer_toolbox.core.flows.flow_trigger import REWARDS, FlowTrigger
from streamer_toolbox.core.flows.flow_trigger_router import FlowTriggerRouter
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.variables.variable_store import VariableStore

BY_ID = FlowTrigger("twitch.redeem", {"reward": "Lizard", "reward_id": "r1"})


class TestRewardIds(unittest.IsolatedAsyncioTestCase):
    """A redeem trigger keeps the reward's id: renaming the reward on Twitch doesn't break it, and the trigger
    takes the new name (on a redeem, and from the reward list when Twitch connects)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name)
        self.actions = ActionRegistry()
        self.calls: list[dict] = []

        async def record(**params):
            self.calls.append(params)

        self.actions.add("a.record", record)
        runner = FlowRunner(self.actions, VariableStore(folder / "v.json"))
        self.store = FlowStore(folder / "flows")
        self.library = FlowLibrary(self.store, FlowStore(folder / "t"), runner, self.actions)
        self.library.save(Flow("lizard", "Lizard", (FlowNode("n1", "a.record", {"by": "${event.user}"}),),
                               (FlowWire("start", "out", "n1"),), (BY_ID,)))
        self.bus = EventBus()
        self.bus.subscribe(FlowTriggerRouter(self.library, runner).handle)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_matches_by_id_when_it_has_one(self) -> None:
        self.assertTrue(BY_ID.matches("twitch.redeem", {"reward": "Lizard (new name)", "reward_id": "r1"}))
        self.assertFalse(BY_ID.matches("twitch.redeem", {"reward": "Lizard", "reward_id": "r2"}))
        by_name = FlowTrigger("twitch.redeem", {"reward": "liz*"})
        self.assertTrue(by_name.matches("twitch.redeem", {"reward": "Lizard", "reward_id": "r9"}))
        empty_id = FlowTrigger("twitch.redeem", {"reward": "Lizard", "reward_id": ""})
        self.assertTrue(empty_id.matches("twitch.redeem", {"reward": "lizard", "reward_id": "r9"}))

    async def test_a_redeem_of_a_renamed_reward_runs_and_renames_the_trigger(self) -> None:
        self.bus.publish("twitch.redeem", {"reward": "Lizard 2.0", "reward_id": "r1", "user": "VexFan"})
        await self.bus.wait_idle()
        self.assertEqual(self.calls, [{"by": "VexFan"}])
        self.assertEqual(self.store.all()[0].triggers[0].match, {"reward": "Lizard 2.0", "reward_id": "r1"})

    async def test_the_reward_list_on_connect_renames_triggers(self) -> None:
        self.bus.publish(REWARDS, {"rewards": [{"id": "r1", "title": "Mini lizard"}, {"id": "r5", "title": "Hi"}]})
        await self.bus.wait_idle()
        self.assertEqual(self.library.get("lizard").triggers[0].match["reward"], "Mini lizard")
        self.assertEqual(self.calls, [])  # the list starts nothing
