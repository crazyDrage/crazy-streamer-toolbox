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


if __name__ == "__main__":
    unittest.main()
