import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.tips.tip_actions import TIP, TipActions
from streamer_toolbox.core.widgets.widget_actions import WidgetActions
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class TestTipActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []
        self.hub = WidgetHub()
        self.actions = ActionRegistry()
        TipActions(self.events).add_to(self.actions)
        WidgetActions(self.hub, WidgetStore(Path(self._dir.name))).add_to(self.actions)

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)
        self.events.subscribe(self.hub.handle)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def test_a_tip_becomes_an_event_for_flows_alerts_and_widgets(self) -> None:
        page = self.hub.listen("goal")
        tip = await self.actions.run("tip.fire", user=" Kit ", amount="4.990", currency="eur", message="snacks",
                                     source="kofi")
        await self.events.wait_idle()
        self.assertEqual(tip, {"user": "Kit", "amount": 4.99, "currency": "EUR", "message": "snacks",
                               "platform": "kofi"})
        self.assertEqual(self.seen, [(TIP, tip)])
        self.assertEqual(set(tip), set(EVENT_FIELDS[TIP]))  # what the Start box offers is what it gives
        self.assertTrue(FlowTrigger(TIP, {"user": "*"}).matches(TIP, tip))
        self.assertEqual(page.get_nowait()["listener"], "tip-latest")
        self.assertEqual(self.hub.session.data["tip-session"], {"count": 1, "amount": 4.99})
        self.assertEqual((await self.actions.run("tip.fire", user="Kit", amount=5))["amount"], 5)  # whole: no .0

    async def test_a_tip_needs_a_real_amount(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be a number"):
            await self.actions.run("tip.fire", user="Kit", amount="five")
        with self.assertRaisesRegex(ValueError, "above 0"):
            await self.actions.run("tip.fire", user="Kit", amount=0)
        self.assertEqual(self.seen, [])

    async def test_a_flow_sends_widgets_an_event_in_streamelements_words(self) -> None:
        goal, chat = self.hub.listen("goal"), self.hub.listen("chat_box")
        sent = await self.actions.run("widget.send_event", listener="host-latest", name="Big", amount="12",
                                      extra={"viewers": 12})
        self.assertEqual(sent, 2)
        self.assertEqual(goal.get_nowait(), {"type": "event", "listener": "host-latest", "event": {
            "type": "host", "name": "Big", "amount": 12, "message": "", "viewers": 12}})
        self.assertEqual(goal.get_nowait()["session"]["host-latest"]["name"], "Big")
        for inbox in (goal, chat):
            while not inbox.empty():
                inbox.get_nowait()
        self.assertEqual(await self.actions.run("widget.send_event", listener="my-thing", widget="goal"), 1)
        self.assertEqual(goal.get_nowait()["listener"], "my-thing")
        self.assertTrue(goal.empty() and chat.empty())  # no session update for a name of his own, only that widget
        with self.assertRaisesRegex(ValueError, "which event"):
            await self.actions.run("widget.send_event", listener=" ")
        self.assertIn("tip-latest", await self.actions.get("widget.send_event").options["listener"]())


if __name__ == "__main__":
    unittest.main()
