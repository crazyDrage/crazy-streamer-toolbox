import asyncio
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.alerts.alert_part import AlertPart
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_router import AlertRouter
from streamer_toolbox.core.alerts.alert_rule import ALERT_EVENTS
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.alerts.alert_variation import AlertVariation
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS


class TestAlertRouter(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "alerts.json"
        self.store = AlertStore(self.path)
        self.queue = AlertQueue(gap=0, sleep=self._sleep)
        self.inbox = self.queue.listen()
        self.router = AlertRouter(self.store, self.queue)

    def tearDown(self) -> None:
        self._dir.cleanup()

    @staticmethod
    async def _sleep(seconds: float) -> None:
        await asyncio.sleep(0)

    async def _texts(self) -> list[str]:
        for _ in range(20):
            await asyncio.sleep(0)
        texts = []
        while not self.inbox.empty():
            texts.append(self.inbox.get_nowait()["alert"]["text"])
        return texts

    def _on(self, event: str, **values) -> None:
        self.store.save(replace(self.store.get(event), on=True, **values))

    async def test_everything_is_off_until_switched_on(self) -> None:
        self.assertEqual([r.title for r in self.store.all()],
                         ["Follow", "Sub", "Resub", "Gift subs", "Cheer", "Raid", "Tip"])
        await self.router.handle("twitch.follow", {"user": "Dragon"})
        self.assertEqual(await self._texts(), [])
        self._on("twitch.follow")
        await self.router.handle("twitch.follow", {"user": "Dragon"})
        await self.router.handle("twitch.chat", {"user": "Dragon", "message": "hi"})  # no alert for chat
        self.assertEqual(await self._texts(), ["Dragon just followed!"])

    async def test_other_platforms_show_the_same_alerts_and_twitch_isnt_shown_twice(self) -> None:
        self._on("twitch.follow")
        self._on("twitch.sub")
        await self.router.handle("follow", {"user": "Ann", "platform": "rumble", "source": "rumble.follow"})
        await self.router.handle("sub", {"user": "Kit", "tier": 1, "gift": False, "platform": "youtube"})
        await self.router.handle("twitch.follow", {"user": "Dragon", "platform": "twitch"})
        await self.router.handle("follow", {"user": "Dragon", "platform": "twitch"})  # the same follow again
        await self.router.handle("chat", {"user": "Ann", "platform": "rumble"})
        self.assertEqual(await self._texts(), ["Ann just followed!", "Kit just subscribed!",
                                               "Dragon just followed!"])

    async def test_the_text_takes_the_events_fields_and_the_amount(self) -> None:
        self._on("twitch.cheer", text="{user}: {amount} bits! \"{message}\"")
        self._on("twitch.resub")
        await self.router.handle("twitch.cheer", {"user": "", "bits": 250, "message": "wow", "anonymous": True})
        await self.router.handle("twitch.resub", {"user": "Kit", "months": 7, "tier": 1, "message": ""})
        self.assertEqual(await self._texts(), ['Someone: 250 bits! "wow"', "Kit subscribed for 7 months!"])

    async def test_the_viewers_message_is_a_second_line_unless_switched_off_or_in_the_text(self) -> None:
        self._on("twitch.cheer")
        cheer = {"user": "Kit", "bits": 100, "message": "take my bits"}
        self.assertEqual(self.store.get("twitch.cheer").alert_for(cheer).message, "take my bits")
        self.store.save(self.store.get("twitch.cheer").without_part(1))
        self.assertEqual(self.store.get("twitch.cheer").alert_for(cheer).message, "")
        self.store.save(self.store.get("twitch.cheer").add_part(AlertPart("message")))
        self._on("twitch.cheer", text="{user}: {message}")
        self.assertEqual(self.store.get("twitch.cheer").alert_for(cheer).message, "")  # not twice
        self.assertFalse(self.store.get("twitch.follow").has_message)

    async def test_a_tip_is_an_alert_too(self) -> None:
        self._on("tip", minimum=3)
        await self.router.handle("tip", {"user": "Kit", "amount": 2, "currency": "EUR", "message": ""})
        await self.router.handle("tip", {"user": "Kit", "amount": 4.99, "currency": "EUR", "message": "snacks"})
        self.assertEqual(await self._texts(), ["Kit tipped 4.99 EUR!"])

    async def test_only_from_an_amount(self) -> None:
        self._on("twitch.raid", minimum=10)
        await self.router.handle("twitch.raid", {"user": "Small", "viewers": 3})
        await self.router.handle("twitch.raid", {"user": "Big", "viewers": 40})
        self.assertEqual(await self._texts(), ["Big is raiding with 40 viewers!"])

    async def test_a_bigger_amount_gets_its_variation(self) -> None:
        self._on("twitch.cheer", sound="", variations=(
            AlertVariation(1000, "{user} is going wild: {amount} bits!"), AlertVariation(100, image="")))
        rule = self.store.get("twitch.cheer")
        self.assertIsNone(rule.variation_for(50))
        self.assertEqual(rule.variation_for(100).minimum, 100)
        self.assertEqual(rule.variation_for(5000).minimum, 1000)  # the highest one reached, whatever the order
        for bits in (50, 500, 5000):
            await self.router.handle("twitch.cheer", {"user": "Kit", "bits": bits, "message": ""})
        await self.router.test("twitch.cheer", amount=1000)
        self.assertEqual(await self._texts(), [
            "Kit cheered 50 bits!", "Kit cheered 500 bits!",  # an empty text stays the alert's own
            "Kit is going wild: 5000 bits!", "TestViewer is going wild: 1000 bits!"])
        self.assertEqual(AlertStore(self.path).get("twitch.cheer").variations, rule.variations)

    async def test_gifted_subs_are_one_alert_for_the_gifter(self) -> None:
        self._on("twitch.sub")
        self._on("twitch.gift")
        await self.router.handle("twitch.gift", {"user": "Santa", "amount": 2, "tier": 1})
        await self.router.handle("twitch.sub", {"user": "A", "tier": 1, "gift": True})
        await self.router.handle("twitch.sub", {"user": "B", "tier": 1, "gift": False})
        self.assertEqual(await self._texts(), ["Santa gifted 2 subs!", "B just subscribed!"])

    async def test_a_missing_picture_doesnt_break_the_event(self) -> None:
        self._on("twitch.follow", image=str(self.path.parent / "gone.png"))
        with self.assertLogs("streamer_toolbox.core.alerts.alert_router", "WARNING"):
            await self.router.handle("twitch.follow", {"user": "Dragon"})
        self.assertEqual(await self._texts(), [])

    async def test_test_shows_the_alert_even_when_off_and_settings_are_kept(self) -> None:
        self._on("twitch.raid", text="RAID {user} x{amount}", seconds=8.0, minimum=5)
        again = AlertStore(self.path)
        self.assertEqual(again.get("twitch.raid"), self.store.get("twitch.raid"))
        self.assertFalse(again.get("twitch.follow").on)
        await self.router.test("twitch.follow")
        await self.router.test("twitch.raid")
        self.assertEqual(await self._texts(), ["TestViewer just followed!", "RAID TestViewer x42"])

    def test_every_alert_event_is_one_twitch_really_sends_with_that_amount_field(self) -> None:
        for event, (_, _, amount, example) in ALERT_EVENTS.items():
            self.assertIn(event, EVENT_FIELDS)
            self.assertTrue(set(example) <= set(EVENT_FIELDS[event]), event)
            if amount:
                self.assertIn(amount, EVENT_FIELDS[event])


if __name__ == "__main__":
    unittest.main()
