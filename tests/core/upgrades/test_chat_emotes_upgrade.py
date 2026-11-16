import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_value import EventValue
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.upgrades.chat_emotes_upgrade import ChatEmotesUpgrade
from streamer_toolbox.core.variables.variable_store import VariableStore


class TestChatEmotesUpgrade(unittest.TestCase):
    """Settings version 7, his "we don't need emotes and emoji_dict. remove the old one"."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        actions = ActionRegistry()
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "templates"),
                                 FlowRunner(actions, VariableStore(folder / "variables")), actions)
        self.flows.load()
        self.events = EventTypeStore(folder / "event_types.json")
        chat = self.events.get("chat")  # as version 6 had it: emotes before picture and emoji_dict
        self.events.save("chat", replace(chat, values=(*chat.values[:7], EventValue("emotes"), *chat.values[7:])))
        self.upgrade = ChatEmotesUpgrade(self.flows, lambda: self.events.remove_values("chat", ("emotes",)))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _send(self, name: str, **params: str) -> None:
        self.flows.save(Flow(name, name.title(), (FlowNode("n1", "event.send.chat", {"user": "x", **params}),)))

    def test_the_value_and_the_send_fields_go(self) -> None:
        self._send("main", emotes="${box.t1.emotes}")  # Twitch's list: not needed any more
        self._send("his", emotes="${box.n6.emoji_dict}")  # his own flow gave the dictionary there
        self._send("both", emotes="${box.t1.emotes}", emoji_dict="${box.n2.emoji_dict}")
        said = self.upgrade.run()
        self.assertNotIn("emotes", [v.name for v in self.events.get("chat").values])
        self.assertIn("emoji_dict", [v.name for v in self.events.get("chat").values])
        self.assertEqual({"user": "x"}, self.flows.get("main").nodes[0].params)
        self.assertEqual({"user": "x", "emoji_dict": "${box.n6.emoji_dict}"}, self.flows.get("his").nodes[0].params)
        self.assertEqual({"user": "x", "emoji_dict": "${box.n2.emoji_dict}"}, self.flows.get("both").nodes[0].params)
        self.assertEqual(4, len(said))
        self.assertEqual([], self.upgrade.run())  # twice changes nothing

    def test_an_imported_flow_too(self) -> None:
        flow = Flow("old", "Old", (FlowNode("n1", "event.send.chat", {"emotes": "${box.t1.emotes}"}),))
        self.assertEqual({}, self.upgrade.flow(flow).nodes[0].params)


if __name__ == "__main__":
    unittest.main()
