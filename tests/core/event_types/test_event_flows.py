import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.event_types.event_flows import EventFlows, action_name, list_name
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
        self.variables = VariableStore(folder / "variables")
        runner = FlowRunner(actions, self.variables)
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "templates"), runner, actions)
        self.flows.load()
        self.event_flows = EventFlows(self.flows, self.events, self.variables)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_chat_is_split_a_main_flow_and_twitchs_own_flow_with_the_picture(self) -> None:
        """His round 90: the main flow leaves out the platforms in the list; Twitch's flow asks for the picture,
        remembers it a while and keeps the file. Its platform goes into the list."""
        main = self.flows.get(self.event_flows.make(self.events.get("chat")))
        listed, check, send = main.nodes
        self.assertEqual(("var.set", "list.contains", action_name("chat")), (listed.action, check.action, send.action))
        self.assertEqual({"name": list_name("chat"), "value": "[]", "only_if_new": True}, listed.params)
        self.assertEqual({"items": "${box.n7}", "value": "${box.t1.platform}"}, check.params)
        self.assertEqual({FlowWire("t1", "out", "n7"), FlowWire("n7", "done", "n8"), FlowWire("n8", "else", "n1")},
                         set(main.wires))
        self.assertNotIn("picture", send.params)  # only Twitch's flow gives them
        self.assertNotIn("emoji_dict", send.params)
        self.assertEqual(["twitch"], self.variables.get("event_chat_platforms_with_own_flow"))

        twitch = next(f for f in self.flows.all() if f.label == "Event: chat · Twitch")
        self.assertEqual("twitch.chat", twitch.triggers[0].kind)
        helper, send = twitch.nodes  # his 11-16: the picture and the emotes in a flow of their own, as a box
        self.assertEqual("flow.twitch_pfp_and_chat_emotes", helper.action)
        self.assertEqual({"user_id": "${box.t1.user_id}", "user_login": "${box.t1.user_login}",
                          "emotes": "${box.t1.emotes}", "message": "${box.t1.message}"}, helper.params)
        self.assertEqual(("${box.n2.picture}", "${box.n2.emoji_dict}"),
                         (send.params["picture"], send.params["emoji_dict"]))
        self.assertEqual({FlowWire("t1", "out", "n2"), FlowWire("n2", "done", "n1")}, set(twitch.wires))

        made = self.flows.get("twitch_pfp_and_chat_emotes")
        self.assertEqual(("Twitch pfp and chat emotes", True), (made.label, made.as_box))
        self.assertEqual([("user_id", ""), ("user_login", ""), ("emotes", ""), ("message", "")],
                         [(i.name, i.default) for i in made.inputs])  # none of them needed
        self.assertEqual(["logic.if", "cache.value", "twitch.profile_picture", "media.keep_locally", "logic.choose",
                          "twitch.emotes", "twitch.bttv_emotes", "object.join", "logic.end"],
                         [node.action for node in made.nodes])
        # his 11-16: a dictionary of each, then the two together
        self.assertEqual({"first": "${box.n8.emoji_dict}", "second": "${box.n6.emoji_dict}"}, made.nodes[-2].params)
        self.assertEqual({"picture": "${box.n5}", "emoji_dict": "${box.n9}"}, made.nodes[-1].params)
        self.assertIn(FlowWire("n1", "else", "n5", "value_2"), made.wires)  # no user id: no picture, no failure
        self.assertIn(FlowWire("n4", "done", "n2", "set"), made.wires)
        # his 11-16: the emote pictures in folders of their own name, shared with any other flow that names them
        self.assertEqual(("twitch_emotes", "bttv_emotes"), (made.nodes[5].params["folder"], made.nodes[6].params["folder"]))
        for flow in (main, twitch, made):  # rule 36: every field a plain value or one whole wire
            for node in flow.nodes:
                for value in node.params.values():
                    self.assertTrue("${" not in str(value) or (str(value).startswith("${box.")
                                                               and str(value).count("${") == 1), value)

    def test_making_it_again_keeps_twitchs_flow_name_and_on_off_and_the_list_has_twitch_once(self) -> None:
        self.event_flows.make(self.events.get("chat"))
        twitch = next(f for f in self.flows.all() if f.label == "Event: chat · Twitch")
        self.flows.save(replace(twitch, enabled=False), twitch.name)
        self.variables.set(list_name("chat"), ["rumble", "twitch"])
        self.event_flows.update_default("chat")
        again = [f for f in self.flows.all() if f.label == "Event: chat · Twitch"]
        self.assertEqual([(twitch.name, False)], [(f.name, f.enabled) for f in again])
        self.assertEqual(["rumble", "twitch"], self.variables.get(list_name("chat")))

    def test_a_chat_type_from_before_the_picture_gets_no_twitch_flow(self) -> None:
        """His "only the default that will get added": settings from before get no picture flow."""
        chat = self.events.get("chat")
        older = replace(chat, values=tuple(v for v in chat.values if v.name not in ("picture", "emoji_dict")))
        flow = self.flows.get(self.event_flows.make(older))
        self.assertEqual(["var.set", "list.contains", action_name("chat")], [node.action for node in flow.nodes])
        self.assertEqual(["Event: chat"], [f.label for f in self.flows.all()])
        self.assertIsNone(self.variables.get(list_name("chat")))

    def test_other_types_check_the_list_then_send(self) -> None:
        flow = self.flows.get(self.event_flows.make(self.events.get("follow")))
        self.assertEqual(["var.set", "list.contains", action_name("follow")], [node.action for node in flow.nodes])
        self.assertEqual(list_name("follow"), flow.nodes[0].params["name"])

    def test_a_one_platform_trigger_gets_no_list(self) -> None:
        flow = self.flows.get(self.event_flows.make(self.events.get("chat_deleted")))
        self.assertEqual([action_name("chat_deleted")], [node.action for node in flow.nodes])
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
