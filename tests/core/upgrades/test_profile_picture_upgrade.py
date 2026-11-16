import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.event_types.event_flows import EventFlows
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.upgrades.profile_picture_upgrade import ProfilePictureUpgrade
from streamer_toolbox.core.variables.variable_store import VariableStore

T = "${box.t1.%s}"


class TestProfilePictureUpgrade(unittest.TestCase):
    """Settings version 5 (his round 90), from the shape dev.7 left."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name)
        actions = ActionRegistry()
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "templates"),
                                 FlowRunner(actions, VariableStore(folder / "variables.json")), actions)
        self.flows.load()
        self.events = EventTypeStore(folder / "event_types.json")
        self.event_flows = EventFlows(self.flows, self.events)
        self.cache = folder / "cache" / "twitch_pictures.json"
        self.cache.parent.mkdir()
        self.cache.write_text("{}", encoding="utf-8")
        self.upgrade = ProfilePictureUpgrade(self.flows, lambda: self.event_flows.update_default("chat"), self.cache)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _old_chat(self, enabled: bool = True) -> None:
        send = {"user": T % "user", "message": T % "message", "picture": "${box.n3.address}"}
        self.flows.save(Flow("event_chat", "Event: chat", (
            FlowNode("n2", "twitch.profile_picture", {"user": T % "user_id", "platform": T % "platform"}),
            FlowNode("n3", "media.keep_locally", {"url": "${box.n2.picture}", "name": T % "user_login"}),
            FlowNode("n1", "event.send.chat", send)),
            (FlowWire("t1", "out", "n2"), FlowWire("n2", "done", "n3"), FlowWire("n3", "done", "n1")),
            (FlowTrigger("chat", {}, "t1"),), folder="Events", enabled=enabled))

    def test_the_old_chat_flow_is_made_new_and_keeps_its_name_and_on_off(self) -> None:
        self._old_chat(enabled=False)
        said = self.upgrade.run()
        self.assertFalse(self.flows.get("event_chat").enabled)
        self.assertIn("list.contains", [node.action for node in self.flows.get("event_chat").nodes])
        twitch = next(f for f in self.flows.all() if f.label == "Event: chat · Twitch")
        helper = next(f for f in self.flows.all() if f.label == "Twitch pfp and chat emotes")  # his 11-16
        self.assertEqual([f"flow.{helper.name}", "event.send.chat"], [node.action for node in twitch.nodes])
        self.assertIn(FlowWire("n4", "done", "n2", "set"), helper.wires)
        picture = next(node for node in helper.nodes if node.action == "twitch.profile_picture")
        self.assertEqual({"user_id": "${box.input.user_id}"}, picture.params)
        self.assertFalse(self.cache.exists())
        self.assertEqual(2, len(said))
        self.assertEqual([], self.upgrade.run())  # twice changes nothing

    def test_a_chat_type_without_the_picture_value_keeps_the_boxes(self) -> None:
        """Seen in the scratch toolbox: settings older than the picture value would get a chat flow without
        them."""
        chat = self.events.get("chat")
        self.events.save("chat", replace(chat, values=tuple(v for v in chat.values
                                                            if v.name not in ("picture", "emoji_dict"))))
        self._old_chat()
        self.upgrade.run()
        flow = self.flows.get("event_chat")
        self.assertEqual(["twitch.profile_picture", "media.keep_locally", "event.send.chat"],
                         [node.action for node in flow.nodes])
        self.assertEqual({"user_id": T % "user_id"}, flow.nodes[0].params)

    def test_his_own_flow_keeps_its_shape_the_field_is_renamed(self) -> None:
        """His own Event: chat (round 90): If before the box, no platform field."""
        self.flows.save(Flow("mine", "Event: chat", (
            FlowNode("n4", "logic.if", {"left": T % "platform", "right": "twitch"}),
            FlowNode("n2", "twitch.profile_picture", {"user": T % "user_id"})),
            (FlowWire("t1", "out", "n4"), FlowWire("n4", "then", "n2")), (FlowTrigger("chat", {}, "t1"),)))
        said = self.upgrade.run()
        flow = self.flows.get("mine")
        self.assertEqual(["logic.if", "twitch.profile_picture"], [node.action for node in flow.nodes])
        self.assertEqual({"user_id": T % "user_id"}, flow.nodes[1].params)
        self.assertEqual(["flow 'Event: chat': Twitch profile picture's user is user_id now",
                          "twitch_pictures.json is gone (Remembered value keeps the addresses now)"], said)

    def test_a_changed_old_chat_flow_is_kept_and_told_about_its_platform(self) -> None:
        self._old_chat()
        flow = self.flows.get("event_chat")
        self.flows.save(Flow(flow.name, flow.label, (*flow.nodes, FlowNode("n9", "logic.if", {})), flow.wires,
                             flow.triggers, folder=flow.folder))
        said = self.upgrade.run()
        self.assertEqual(4, len(self.flows.get("event_chat").nodes))
        self.assertIn("put an If (platform is twitch) before it", said[1])

    def test_an_imported_flow_gets_the_new_field(self) -> None:
        old = Flow("x", "X", (FlowNode("n2", "twitch.profile_picture", {"user": "kit", "platform": "twitch"}),), ())
        self.assertEqual({"user_id": "kit"}, self.upgrade.flow(old).nodes[0].params)


if __name__ == "__main__":
    unittest.main()
