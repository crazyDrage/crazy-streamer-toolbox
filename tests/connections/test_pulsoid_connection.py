import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path

import httpx

from streamer_toolbox.connections.heartrate.heart_rate import HeartRate
from streamer_toolbox.connections.pulsoid_connection import PulsoidConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_json_socket_server import FakeJsonSocketServer

TOKEN = "pulsoid-secret-token"
WIDGET = "11111111-2222-3333-4444-555555555555"


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestPulsoidConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.token = Path(self._dir.name) / "pulsoid_token.txt"
        self.token.write_text(TOKEN, encoding="utf-8")
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)
        self.heart = HeartRate(self.events)
        self.actions = ActionRegistry()
        self.heart.add_to(self.actions)

    def tearDown(self) -> None:
        self._dir.cleanup()

    async def test_each_change_of_the_heart_rate_is_an_event_and_the_box_reads_the_last_one(self) -> None:
        self.assertEqual(await self.actions.run("heartrate.get"), {"bpm": 0, "source": ""})
        async with FakeJsonSocketServer() as server:
            connection = PulsoidConnection({"enabled": True}, self.token, self.heart,
                                           server.url + "/real_time?access_token=", retry_delay=0.05)
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertEqual(server.paths, [f"/real_time?access_token={TOKEN}"])
            for rate in (72, 72, 0, "x", 75):  # the same again, and nonsense, are no news
                await server.tell({"measured_at": 1625310655000, "data": {"heart_rate": rate}})
            await until(lambda: len(self.seen) == 2)
            self.assertEqual(self.seen, [("heartrate", {"bpm": 72, "source": "pulsoid"}),
                                         ("heartrate", {"bpm": 75, "source": "pulsoid"})])
            self.assertEqual(set(self.seen[0][1]), set(EVENT_FIELDS["heartrate"]))
            self.assertEqual(await self.actions.run("heartrate.get"), {"bpm": 75, "source": "pulsoid"})
            self.assertTrue(self.actions.get("heartrate.get").live)
            await connection.stop()

    async def test_a_widget_link_is_enough_the_feed_is_asked_from_pulsoid(self) -> None:
        self.token.write_text(f"https://pulsoid.net/widget/view/{WIDGET}\n", encoding="utf-8")
        asked: list[dict] = []
        async with FakeJsonSocketServer() as server:
            feed = server.url + "/real_time?access_token=widget-token&response_mode=legacy_json"

            def pulsoid(request: httpx.Request) -> httpx.Response:
                asked.append(json.loads(request.content))
                known = asked[-1]["params"]["widgetId"] == WIDGET and not self.gone
                return httpx.Response(200, json={"result": {"ramielUrl": feed, "token": "widget-token"}} if known
                                      else {"error": {"message": "not found"}})

            self.gone = False
            connection = PulsoidConnection({"enabled": True}, self.token, self.heart, "ws://127.0.0.1:1/?t=",
                                           retry_delay=0.05, transport=httpx.MockTransport(pulsoid))
            self.assertEqual((await connection.test({})).state, ConnectionState.CONNECTED)
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertEqual((asked[0]["method"], asked[0]["params"]), ("getWidget", {"widgetId": WIDGET}))
            self.assertEqual(server.paths[-1], "/real_time?access_token=widget-token&response_mode=legacy_json")
            self.assertEqual(connection.status.facts, (("Feed", "heart rate, from the widget link"),))
            await server.tell({"timestamp": 1791661631028, "data": {"heartRate": 51}})  # as the real one said
            await until(lambda: self.seen == [("heartrate", {"bpm": 51, "source": "pulsoid"})])
            await connection.stop()
            self.gone = True  # a link Pulsoid doesn't know: said in words, nothing of the link shown
            status = await connection.test({})
            self.assertIn("Pulsoid knows no widget with that link", status.detail)
            self.assertNotIn(WIDGET, status.detail)

    async def test_without_a_token_it_says_so_and_never_shows_one(self) -> None:
        self.token.write_text("", encoding="utf-8")
        connection = PulsoidConnection({"enabled": True}, self.token, self.heart, "ws://127.0.0.1:1/?t=",
                                       retry_delay=0.05)
        self.assertIn("No token or widget link yet", (await connection.test({})).detail)
        await connection.start()
        await until(lambda: "No token or widget link yet" in connection.status.detail)
        self.token.write_text(TOKEN, encoding="utf-8")
        await until(lambda: "trying again" in connection.status.detail and "No token" not in connection.status.detail)
        self.assertNotIn(TOKEN, connection.status.detail)
        self.assertNotIn(TOKEN, (await connection.test({})).detail)
        await connection.stop()
        self.assertFalse(PulsoidConnection({}, self.token, self.heart).settings["enabled"])


if __name__ == "__main__":
    unittest.main()
