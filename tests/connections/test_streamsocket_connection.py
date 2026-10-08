import asyncio
import tempfile
import time
import unittest
from pathlib import Path

from streamer_toolbox.connections.streamsocket.streamsocket_client import streamsocket_event
from streamer_toolbox.connections.streamsocket_connection import StreamSocketConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_streamsocket_server import FakeStreamSocketServer

# the documented shape of a redemption (streamsocket.kadokta.com/documentation/api)
REDEEMED = {"event_id": "ev1", "event_display_name": "Lizard", "product_sku": "sku100", "product_bits": 100,
            "user_id": "77", "user_display_name": "Kit", "is_test": True, "category_ids": ["fun"]}


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestStreamSocketConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.secret = Path(self._dir.name) / "streamsocket_secret.txt"
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _connection(self, server: FakeStreamSocketServer, twitch_id: str = "42", **settings) -> StreamSocketConnection:
        return StreamSocketConnection({"enabled": True, **settings}, self.secret, self.events, lambda: twitch_id,
                                      url=server.url)

    def test_a_redemption_as_the_toolboxes_event(self) -> None:
        event = streamsocket_event(REDEEMED)
        self.assertEqual(event, {"event": "Lizard", "event_id": "ev1", "bits": 100, "user": "Kit", "user_id": "77",
                                 "categories": ["fun"], "test": True, "platform": "twitch"})
        self.assertEqual(set(event), set(EVENT_FIELDS["streamsocket.event"]))
        self.assertEqual(streamsocket_event({"event_id": "ev2", "product_bits": "free"})["event"], "ev2")

    async def test_it_is_off_until_switched_on_and_needs_the_secret_and_a_channel(self) -> None:
        async with FakeStreamSocketServer() as server:
            self.assertFalse(StreamSocketConnection({}, self.secret, self.events).settings["enabled"])
            connection = self._connection(server)
            await connection.start()
            self.assertIn("No secret yet", connection.status.detail)
            self.secret.write_text("the-secret", encoding="utf-8")
            connection = self._connection(server, twitch_id="")
            await connection.start()
            self.assertIn("No channel yet", connection.status.detail)
            self.assertEqual(server.connections, 0)

    async def test_listens_on_his_channel_answers_the_servers_checks_and_passes_events_on(self) -> None:
        self.secret.write_text("the-secret\n", encoding="utf-8")
        async with FakeStreamSocketServer() as server:
            connection = self._connection(server)
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.CONNECTED)
            self.assertTrue(server.paths[0].endswith("/channel/42"))  # the Twitch login's channel
            await server.send("request_connection_check")
            await server.send("notification_event", REDEEMED)
            await server.send("request_event_data", {**REDEEMED, "event_display_name": "Hug"}, "req-9")
            await server.send("notification_config_update", {"time": 1, "events": []})
            await until(lambda: len(self.seen) == 2)
            self.assertEqual([(kind, data["event"]) for kind, data in self.seen],
                             [("streamsocket.event", "Lizard"), ("streamsocket.event", "Hug")])
            await until(lambda: len(server.received) == 3)
            self.assertEqual(server.received[1], {"type": "response_connection_check",
                                                  "data": {"secret": "the-secret", "active": True}})
            self.assertEqual((server.received[2]["type"], server.received[2]["request_id"]),
                             ("response_event_data", "req-9"))  # the viewer isn't left waiting
            await connection.stop()
            self.assertEqual(connection.status.state, ConnectionState.OFF)

    async def test_a_typed_channel_wins_and_a_wrong_secret_isnt_tried_again(self) -> None:
        self.secret.write_text("old-secret", encoding="utf-8")
        async with FakeStreamSocketServer() as server:
            connection = self._connection(server, channel_id="99")
            tried = await connection.test(connection.settings)
            self.assertEqual(tried.state, ConnectionState.ERROR)
            self.assertIn("refused the secret", tried.detail)
            self.assertTrue(server.paths[0].endswith("/channel/99"))
            await connection.start()
            await until(lambda: connection.status.state is ConnectionState.ERROR)
            await asyncio.sleep(0.2)
            self.assertEqual(server.connections, 2)  # the test and one start: no asking in a loop
            self.assertNotIn("old-secret", connection.status.detail)
            await connection.stop()
            self.secret.write_text("the-secret", encoding="utf-8")
            good = await connection.test(connection.settings)
            self.assertEqual((good.state, good.facts), (ConnectionState.CONNECTED, (("Channel", "99"),)))


if __name__ == "__main__":
    unittest.main()
