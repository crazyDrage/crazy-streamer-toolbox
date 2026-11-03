import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.tips.boxes.tip_box import TIP
from streamer_toolbox.core.tips.tip_actions import TipActions
from streamer_toolbox.core.widgets.widget_hub import WidgetHub


class TestTipActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []
        self.hub = WidgetHub()
        self.actions = ActionRegistry()
        TipActions(self.events).add_to(self.actions)

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)
        self.events.subscribe(self.hub.handle)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def test_a_tip_becomes_an_event_for_flows_alerts_and_widgets(self) -> None:
        tip = await self.actions.run("tip.fire", user=" Kit ", amount="4.990", currency="eur", message="snacks",
                                     source="kofi")
        await self.events.wait_idle()
        self.assertEqual(tip, {"user": "Kit", "amount": 4.99, "currency": "EUR", "message": "snacks",
                               "platform": "kofi"})
        self.assertEqual(self.seen, [(TIP, tip)])
        self.assertEqual(set(tip), set(EVENT_FIELDS[TIP]))  # what the Start box offers is what it gives
        self.assertTrue(FlowTrigger(TIP, {"user": "*"}).matches(TIP, tip))
        self.assertEqual(self.hub.session.data["tip-session"], {"count": 1, "amount": 4.99})
        self.assertEqual((await self.actions.run("tip.fire", user="Kit", amount=5))["amount"], 5)  # whole: no .0

    async def test_a_tip_needs_a_real_amount(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be a number"):
            await self.actions.run("tip.fire", user="Kit", amount="five")
        with self.assertRaisesRegex(ValueError, "above 0"):
            await self.actions.run("tip.fire", user="Kit", amount=0)
        self.assertEqual(self.seen, [])


if __name__ == "__main__":
    unittest.main()
