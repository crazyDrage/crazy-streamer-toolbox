import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.event_types.event_flows import EventFlows
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_value import EventValue
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import FlowWire
from streamer_toolbox.core.upgrades.emoji_dict_upgrade import EmojiDictUpgrade
from streamer_toolbox.core.variables.variable_store import VariableStore

OLD = ("user", "message", "color", "role", "platform", "user_id", "message_id")  # v0.4.1's chat values


class TestEmojiDictUpgrade(unittest.TestCase):
    """Settings version 6: the chat type that came with the toolbox gets picture and emoji_dict, and the chat flows
    the toolbox made, unchanged, are made new (his "the settings files of the last version may need to be
    converted into the current settings", "check the dev versions, too")."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.path = folder / "event_types.json"
        events = EventTypeStore(self.path)
        chat = events.get("chat")  # as v0.4.1 had it: no picture, no emoji_dict
        events.save("chat", replace(chat, values=tuple(v for v in chat.values if v.name in OLD)))
        self.events = EventTypeStore(self.path)
        actions = ActionRegistry()
        variables = VariableStore(folder / "variables")
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "templates"),
                                 FlowRunner(actions, variables), actions)
        self.flows.load()
        self.event_flows = EventFlows(self.flows, self.events, variables)
        self.upgrade = EmojiDictUpgrade(
            lambda: self.events.add_values("chat", (EventValue("picture"), EventValue("emoji_dict"))),
            self.flows, lambda: self.event_flows.update_default("chat"))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _v041_chat(self, **changed: str) -> None:
        params = {key: f"${{box.t1.{key}}}" for key in OLD} | changed
        self.flows.save(Flow("event_chat", "Event: chat", (FlowNode("n1", "event.send.chat", params),),
                             (FlowWire("t1", "out", "n1"),), (FlowTrigger("chat", {}, "t1"),), folder="Events"))

    def test_the_chat_type_gets_both_at_the_end_once(self) -> None:
        self.assertEqual(["the chat event got the value picture", "the chat event got the value emoji_dict"],
                         self.upgrade.run())
        self.assertEqual(["picture", "emoji_dict"], [v.name for v in EventTypeStore(self.path).get("chat").values][-2:])
        self.assertEqual([], self.upgrade.run())

    def test_a_chat_type_he_made_himself_stays_as_it_is(self) -> None:
        chat = self.events.get("chat")
        self.events.save("chat", replace(chat, default=False))
        self.assertEqual([], self.upgrade.run())
        self.assertNotIn("emoji_dict", [v.name for v in self.events.get("chat").values])

    def test_v041s_unchanged_chat_flow_is_made_new_with_picture_and_emotes(self) -> None:
        self._v041_chat()
        said = self.upgrade.run()
        self.assertIn("flow 'Event: chat': made new (the picture and the emotes)", said)
        twitch = next(f for f in self.flows.all() if f.label == "Event: chat · Twitch")
        send = next(node for node in twitch.nodes if node.action == "event.send.chat")
        self.assertEqual(("${box.n2.picture}", "${box.n2.emoji_dict}"), (send.params["picture"],
                                                                         send.params["emoji_dict"]))
        self.assertIn("list.contains", [node.action for node in self.flows.get("event_chat").nodes])

    def test_a_chat_flow_changed_by_hand_stays(self) -> None:
        self._v041_chat(message="${box.t1.message}!")
        self.upgrade.run()
        self.assertEqual(["event.send.chat"], [node.action for node in self.flows.get("event_chat").nodes])
        self.assertNotIn("Event: chat · Twitch", [f.label for f in self.flows.all()])

    def test_step_5s_twitch_flow_without_emoji_dict_is_made_new(self) -> None:
        """dev.6 / dev.7's settings: step 5 made Event: chat · Twitch while the type had no emoji_dict yet."""
        chat = self.events.get("chat")
        self.events.save("chat", replace(chat, values=(*chat.values, EventValue("picture"))))
        self.event_flows.update_default("chat")  # what step 5 does
        twitch = next(f for f in self.flows.all() if f.label == "Event: chat · Twitch")
        self.assertNotIn("emoji_dict", twitch.nodes[-1].params)
        self.upgrade.run()
        again = self.flows.get(twitch.name)
        self.assertEqual("${box.n2.emoji_dict}", again.nodes[-1].params["emoji_dict"])
        self.assertEqual([], self.upgrade.run()[1:])  # nothing more to make new


if __name__ == "__main__":
    unittest.main()
