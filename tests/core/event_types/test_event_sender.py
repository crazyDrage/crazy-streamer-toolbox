import asyncio
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.alerts.alert_input import AlertInput
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.event_types.event_sender import EventSender, widget_event
from streamer_toolbox.core.event_types.event_type import EventType
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_value import EventValue
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class TestEventSender(unittest.IsolatedAsyncioTestCase):
    """His round 78: an event's box sends it to every widget and alert that uses it."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.events = EventTypeStore(folder / "event_types.json")
        self.widgets = WidgetStore(folder / "widgets")
        self.hub = WidgetHub()
        self.alerts = AlertStore(folder / "alerts.json")
        self.queue = AlertQueue(gap=0, sleep=self._sleep)
        self.overlay = self.queue.listen()
        self.sender = EventSender(self.events, self.widgets, self.hub, self.alerts, self.queue)

    def tearDown(self) -> None:
        self._dir.cleanup()

    @staticmethod
    async def _sleep(seconds: float) -> None:
        await asyncio.sleep(0)

    async def test_every_widget_and_alert_that_uses_it_gets_it(self) -> None:
        self.widgets.save(Widget("box", events=("follow",)))
        self.widgets.save(Widget("other", events=("chat",)))
        box, other = self.hub.listen("box"), self.hub.listen("other")
        self.alerts.save(replace(self.alerts.get("follow"), on=True))
        result = await self.sender.send("follow", {"user": "Kit"})
        self.assertEqual(result, {"pages": 1, "alerts": 1, "in_front": 0})
        message = box.get_nowait()
        self.assertEqual((message["listener"], message["event"]["name"], message["event"]["user"]),
                         ("follower-latest", "Kit", "Kit"))
        self.assertTrue(other.empty())
        for _ in range(10):
            await asyncio.sleep(0)
        self.assertEqual(self.overlay.get_nowait()["alert"]["text"], "Kit just followed!")

    async def test_only_to_one_of_them(self) -> None:
        self.widgets.save(Widget("a", events=("follow",)))
        self.widgets.save(Widget("b", events=("follow",)))
        a, b = self.hub.listen("a"), self.hub.listen("b")
        self.alerts.save(replace(self.alerts.get("follow"), on=True))
        result = await self.sender.send("follow", {"user": "Kit"}, only_to="widget b")
        self.assertEqual((result["pages"], result["alerts"]), (1, 0))
        self.assertTrue(a.empty())
        self.assertFalse(b.empty())

    async def test_an_alert_that_is_off_or_below_its_smallest_amount_plays_nothing(self) -> None:
        self.assertEqual((await self.sender.send("raid", {"user": "Big", "viewers": 40}))["alerts"], 0)
        self.alerts.save(replace(self.alerts.get("raid"), on=True, minimum=10))
        self.assertEqual((await self.sender.send("raid", {"user": "Small", "viewers": 3}))["alerts"], 0)
        self.assertEqual((await self.sender.send("raid", {"user": "Big", "viewers": "40"}))["alerts"], 1)
        for _ in range(10):
            await asyncio.sleep(0)
        self.assertEqual(self.overlay.get_nowait()["alert"]["text"], "Big is raiding with 40 viewers!")

    async def test_a_sound_value_makes_a_soundboard(self) -> None:
        board = Path(self._dir.name) / "lizard.ogg"
        board.write_bytes(b"ogg")
        self.events.add("soundboard", (EventValue("sound", kind="sound"),))
        rule = self.alerts.add("Soundboard", (AlertInput("sound", "sound"),), event="soundboard")
        self.alerts.save(replace(rule, on=True))
        await self.sender.send("soundboard", {"sound": f'"{board}"'})  # "Copy as path" quotes too
        for _ in range(10):
            await asyncio.sleep(0)
        self.assertTrue(self.overlay.get_nowait()["alert"]["sound"].startswith("/overlay/file/"))

    async def test_an_event_that_is_gone(self) -> None:
        with self.assertRaisesRegex(KeyError, "Overlay → Events"):
            await self.sender.send("nothing", {})

    def test_what_a_widgets_code_gets(self) -> None:
        own = EventType("lizard", (EventValue("count", "1", "number", ("amount",)), EventValue("who", "Kit")))
        values = own.filled({"count": "7"})
        self.assertEqual(widget_event(own, values), {"count": 7, "amount": 7, "who": "Kit"})
        chat = self.events.get("chat")
        event = widget_event(chat, chat.filled({"user": "Ann", "message": "hi", "platform": "rumble"}))
        self.assertEqual((event["service"], event["data"]["displayName"], event["displayName"]),
                         ("rumble", "Ann", "Ann"))


if __name__ == "__main__":
    unittest.main()
