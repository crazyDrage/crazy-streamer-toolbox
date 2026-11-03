import asyncio
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.event_types.event_actions import EventActions
from streamer_toolbox.core.event_types.event_flows import FOLDER, EventFlows
from streamer_toolbox.core.event_types.event_sender import EventSender
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_users import EventUsers
from streamer_toolbox.core.events.common_events import SAME, common
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_runner import FlowRunner
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.flows.flow_trigger_router import FlowTriggerRouter
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore

CHAT_JS = """window.addEventListener('onEventReceived', obj => {
  if (obj.detail.listener === 'message') show(obj.detail.event);
  else if (obj.detail.listener === "subscriber-latest") sub(obj.detail.event);
});"""


class TestEventUsers(unittest.IsolatedAsyncioTestCase):
    """His round 78: widgets and alerts pick event types; one flow per type sends it to all of them."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.actions = ActionRegistry()
        self.events = EventTypeStore(folder / "event_types.json")
        self.widgets = WidgetStore(folder / "widgets")
        self.alerts = AlertStore(folder / "alerts.json")
        self.hub = WidgetHub()
        self.queue = AlertQueue(gap=0, sleep=self._sleep)
        self.overlay = self.queue.listen()
        runner = FlowRunner(self.actions, VariableStore(folder / "variables.json"))
        self.flows = FlowLibrary(FlowStore(folder / "flows"), FlowStore(folder / "templates"), runner, self.actions)
        self.flows.load()
        self.event_flows = EventFlows(self.flows, self.events)
        self.users = EventUsers(self.events, self.widgets, self.alerts, self.event_flows)
        self.boxes = EventActions(self.events, EventSender(self.events, self.widgets, self.hub, self.alerts,
                                                           self.queue), self.users.choices)
        self.boxes.add_to(self.actions)
        self.events.on_change = lambda: (self.boxes.sync(), self.users.follow_events())
        self.router = FlowTriggerRouter(self.flows, runner)

    def tearDown(self) -> None:
        self._dir.cleanup()

    @staticmethod
    async def _sleep(seconds: float) -> None:
        await asyncio.sleep(0)

    async def _event(self, kind: str, data: dict) -> None:
        await self.router.handle(kind, data)
        if kind in SAME:
            await self.router.handle(SAME[kind], common(kind, data))
        for _ in range(30):
            await asyncio.sleep(0)

    async def test_a_new_toolbox_gets_a_flow_per_event_its_alerts_use_once(self) -> None:
        made = self.users.start()
        self.assertEqual(len(made), 7)  # follow, sub, resub, gift, cheer, raid, tip
        self.assertTrue(all(self.flows.get(name).folder == FOLDER for name in made))
        self.assertTrue(self.flows.folder_settings.hidden(FOLDER))
        self.assertFalse(self.events.get("follow").hidden)
        self.assertTrue(self.events.get("chat").hidden)  # nothing uses it
        self.flows.delete(made[0])
        self.assertEqual(self.users.start(), [])  # one he deleted isn't made again

    async def test_a_follow_reaches_the_widget_and_the_alert_through_the_events_flow(self) -> None:
        self.users.start()
        self.alerts.save(replace(self.alerts.get("follow"), on=True))
        self.widgets.save(Widget("box", js="if (listener === 'follower-latest') {}"))
        self.assertEqual(self.users.give_events("box"), [])  # follow has its flow already
        self.assertEqual(self.users.events_of("box"), ("follow",))
        page = self.hub.listen("box")
        await self._event("twitch.follow", {"user": "Kit", "platform": "twitch"})
        self.assertEqual(page.get_nowait()["event"]["name"], "Kit")
        self.assertEqual(self.overlay.get_nowait()["alert"]["text"], "Kit just followed!")

    async def test_gifted_subs_play_only_the_gifters_alert(self) -> None:
        """His answer 1: "gifted subs should not get the sub alert, but the gifter needs an alert. X gifted Y subs"."""
        self.users.start()
        for id_ in ("sub", "gift"):
            self.alerts.save(replace(self.alerts.get(id_), on=True))
        await self._event("twitch.gift", {"user": "Kit", "amount": 5, "tier": 1, "platform": "twitch"})
        for _ in range(5):
            await self._event("twitch.sub", {"user": "Someone", "tier": 1, "gift": True, "platform": "twitch"})
        self.assertEqual(self.overlay.get_nowait()["alert"]["text"], "Kit gifted 5 subs!")
        self.assertTrue(self.overlay.empty())
        await self._event("twitch.sub", {"user": "Ann", "tier": 1, "gift": False, "platform": "twitch"})
        self.assertEqual(self.overlay.get_nowait()["alert"]["text"], "Ann just subscribed!")

    async def test_a_widget_gets_the_events_its_code_listens_for(self) -> None:
        self.widgets.save(Widget("chat_box", js=CHAT_JS))
        made = self.users.give_events("chat_box")
        self.assertEqual(self.users.events_of("chat_box"), ("chat", "sub", "resub", "gift"))
        self.assertEqual(len(made), 4)
        self.assertFalse(self.events.get("chat").hidden)
        self.assertEqual(self.users.give_events("chat_box"), [])  # once
        self.assertEqual(self.users.users("chat"), ["Widget chat_box"])

    async def test_an_alert_on_an_event_has_its_values_and_follows_a_renamed_one(self) -> None:
        kind = self.events.add("lizard")
        self.events.save("lizard", replace(kind, values=(self.events.get("follow").values[0],)))
        rule, made = self.users.new_alert("Lizard", "lizard")
        self.assertEqual(([i.name for i in rule.inputs], rule.text, len(made)), (["user"], "{user}", 1))
        self.users.rename_value("lizard", "user", "who")
        rule = self.alerts.get(rule.id)
        self.assertEqual(([i.name for i in rule.inputs], rule.text), (["who"], "{who}"))
        box = self.flows.get(made[0]).nodes[0]
        self.assertIn("who", self.actions.get(box.action).handler.__signature__.parameters)
        self.users.rename_event("lizard", "lizards")
        self.assertEqual(self.alerts.get(rule.id).event, "lizards")
        self.assertEqual(self.flows.get(made[0]).nodes[0].action, "event.send.lizards")
        self.assertIsNotNone(self.actions.get("event.send.lizards"))
        with self.assertRaises(ValueError):
            self.users.rename_event("lizards", "follow")

    async def test_only_to_offers_who_uses_it(self) -> None:
        self.users.start()
        self.widgets.save(Widget("box", events=("raid",)))
        self.assertEqual(self.users.choices("raid"), {"widget box": "Widget box", "alert raid": "Alert Raid"})
        self.assertEqual(self.users.unreached("raid"), [])


if __name__ == "__main__":
    unittest.main()
