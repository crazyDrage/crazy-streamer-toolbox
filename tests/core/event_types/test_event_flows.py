import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.event_types.event_flows import EventFlows, action_name
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestEventFlows(unittest.TestCase):
    """An event type's own flow; the chat's asks for the profile picture first (his 11-14)."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.events = EventTypeStore(folder / "event_types.json")
        actions = ActionRegistry()
        runner = FlowRunner(actions, VariableStore(folder / "variables.json"))
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "templates"), runner, actions)
        self.flows.load()
        self.event_flows = EventFlows(self.flows, self.events)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_the_chats_flow_gets_the_picture_from_twitch_and_keeps_it_locally(self) -> None:
        flow = self.flows.get(self.event_flows.make(self.events.get("chat")))
        picture, keep, send = (next(node for node in flow.nodes if node.action == action)
                               for action in ("twitch.profile_picture", "media.keep_locally", action_name("chat")))
        self.assertEqual({"user": "${box.t1.user_id}", "platform": "${box.t1.platform}"}, picture.params)
        self.assertEqual({"url": "${box.%s.picture}" % picture.id}, keep.params)
        self.assertEqual("${box.%s.address}" % keep.id, send.params["picture"])
        self.assertEqual("${box.t1.message}", send.params["message"])
        self.assertEqual({FlowWire("t1", "out", picture.id), FlowWire(picture.id, "done", keep.id),
                          FlowWire(keep.id, "done", send.id)}, set(flow.wires))

    def test_a_chat_type_from_before_the_picture_keeps_its_old_flow(self) -> None:
        """His "only the default that will get added": settings from before get no box."""
        chat = self.events.get("chat")
        older = replace(chat, values=tuple(v for v in chat.values if v.name != "picture"))
        flow = self.flows.get(self.event_flows.make(older))
        self.assertEqual([action_name("chat")], [node.action for node in flow.nodes])
        self.assertNotIn("picture", flow.nodes[0].params)

    def test_other_types_wire_start_to_send(self) -> None:
        flow = self.flows.get(self.event_flows.make(self.events.get("follow")))
        self.assertEqual([action_name("follow")], [node.action for node in flow.nodes])
        self.assertEqual((FlowWire("t1", "out", "n1"),), flow.wires)


    def test_default_flows_bring_an_events_flow_once(self) -> None:
        """His 11-14: adding Twitch's default flows adds the events and their flows too."""
        name = self.event_flows.add_default("follow")
        self.assertEqual("Event: follow", self.flows.get(name).label)
        self.assertFalse(self.events.get("follow").hidden)
        self.assertEqual("", self.event_flows.add_default("follow"))  # there already

    def test_a_deleted_default_type_comes_back_with_its_flow(self) -> None:
        self.events.delete("raid")
        name = self.event_flows.add_default("raid")
        self.assertIsNotNone(self.events.get("raid"))
        self.assertEqual(action_name("raid"), self.flows.get(name).nodes[-1].action)
        self.assertEqual("", self.event_flows.add_default("not_a_default"))

    def test_an_update_makes_his_flow_the_default_again(self) -> None:
        name = self.event_flows.add_default("cheer")
        his = self.flows.get(name)
        self.flows.save(replace(his, description="mine", enabled=False, nodes=()), name)
        self.assertEqual(name, self.event_flows.update_default("cheer"))
        flow = self.flows.get(name)
        self.assertEqual((False, action_name("cheer")), (flow.enabled, flow.nodes[-1].action))
        self.assertNotEqual("mine", flow.description)

    def test_twitchs_event_types_all_have_a_default_flow(self) -> None:
        from streamer_toolbox.connections.twitch_connection import TwitchConnection
        from streamer_toolbox.core.event_types.event_flows import TRIGGERS
        self.assertTrue(set(TwitchConnection.event_types(None)) <= set(TRIGGERS))

if __name__ == "__main__":
    unittest.main()
