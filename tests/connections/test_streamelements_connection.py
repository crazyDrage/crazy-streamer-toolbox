import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.streamelements.astro_events import ACTIVITY, activity_events
from streamer_toolbox.connections.streamelements_connection import StreamElementsConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_astro_server import FakeAstroServer

# a real message of the feed (2026-10-03, a dashboard test tip), ids replaced
MOCK_TIP = {"id": "a3f2", "ts": "2026-10-03T13:28:34.751Z", "type": "message", "topic": "channel.activities",
            "room": "room1", "data": {"channel": "room1", "provider": "twitch", "type": "tip",
                                      "createdAt": "2026-10-03T13:28:25.746Z", "isMock": True,
                                      "data": {"username": "davida", "displayName": "Davida", "providerId": "1",
                                               "amount": 10, "avatar": "https://example.org/a.jpg"},
                                      "_id": "6ac1", "activityId": "6ac1", "sessionEventsCount": 1}}


class TestStreamElementsConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.token = Path(self._dir.name) / "streamelements_token.txt"
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _connection(self, server: FakeAstroServer, enabled: bool = True) -> StreamElementsConnection:
        return StreamElementsConnection({"enabled": enabled}, self.token, self.events, url=server.url)

    async def _settle(self) -> None:
        for _ in range(50):
            await asyncio.sleep(0.01)
        await self.events.wait_idle()

    def test_a_tip_is_an_activity_and_the_toolboxes_tip(self) -> None:
        events = activity_events(MOCK_TIP)
        self.assertEqual(events, [
            (ACTIVITY, {"type": "tip", "user": "Davida", "user_login": "davida", "amount": 10, "message": "",
                        "test": True, "platform": "twitch"}),
            ("tip", {"user": "Davida", "amount": 10, "currency": "", "message": "", "platform": "streamelements"})])
        for kind, data in events:
            self.assertEqual(set(data), set(EVENT_FIELDS[kind]))  # what the Start box offers is what comes

    def test_other_activities_and_other_messages(self) -> None:
        cheer = {"type": "message", "topic": "channel.activities", "data": {
            "provider": "twitch", "type": "cheer", "data": {"username": "fiann", "amount": 1000,
                                                            "message": " Cheer1000"}}}
        self.assertEqual(activity_events(cheer), [(ACTIVITY, {
            "type": "cheer", "user": "fiann", "user_login": "fiann", "amount": 1000, "message": "Cheer1000",
            "test": False, "platform": "twitch"})])
        self.assertEqual(activity_events({"type": "message", "topic": "channel.session.update", "data": {}}), [])
        self.assertEqual(activity_events({"type": "welcome", "data": {}}), [])

    async def test_it_is_off_until_switched_on_and_needs_the_token_file(self) -> None:
        async with FakeAstroServer() as server:
            off = StreamElementsConnection({}, self.token, self.events, url=server.url)
            self.assertFalse(off.settings["enabled"])
            connection = self._connection(server)
            await connection.start()
            self.assertEqual(connection.status.state, ConnectionState.ERROR)
            self.assertIn("No token yet", connection.status.detail)
            self.assertEqual(server.subscriptions, [])

    async def test_listens_with_the_token_and_passes_activities_on(self) -> None:
        self.token.write_text("my.jwt.token\nroom1\n", encoding="utf-8")
        async with FakeAstroServer() as server:
            connection = self._connection(server)
            await connection.start()
            await asyncio.wait_for(server.subscribed.wait(), 5)
            await self._settle()
            self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
            self.assertEqual(server.subscriptions, [{"topic": "channel.activities", "token": "my.jwt.token",
                                                     "token_type": "jwt", "room": "room1"}])
            await server.activity("tip", {"username": "kit", "displayName": "Kit", "amount": 4.99,
                                          "currency": "eur", "message": "snacks"})
            await server.activity("merch", {"username": "bea", "amount": 13}, message_id="same")
            await server.activity("merch", {"username": "bea", "amount": 13}, message_id="same")  # sent twice
            await self._settle()
            self.assertEqual([(kind, data.get("type", "")) for kind, data in self.seen],
                             [(ACTIVITY, "tip"), ("tip", ""), (ACTIVITY, "merch")])
            self.assertEqual(self.seen[1][1], {"user": "Kit", "amount": 4.99, "currency": "EUR", "message": "snacks",
                                               "platform": "streamelements"})
            await connection.stop()
            self.assertEqual(connection.status.state, ConnectionState.OFF)

    async def test_it_subscribes_again_when_asked_to_reconnect(self) -> None:
        self.token.write_text("my.jwt.token\nroom1", encoding="utf-8")
        async with FakeAstroServer() as server:
            connection = self._connection(server)
            await connection.start()
            await asyncio.wait_for(server.subscribed.wait(), 5)
            await self._settle()
            server.subscribed.clear()
            await server.ask_reconnect()
            await asyncio.wait_for(server.subscribed.wait(), 5)
            self.assertEqual(len(server.subscriptions), 2)
            await connection.stop()

    async def test_a_refused_token_shows_on_the_tab_and_isnt_asked_again(self) -> None:
        self.token.write_text("old.jwt.token", encoding="utf-8")
        async with FakeAstroServer(accept=False) as server:
            connection = self._connection(server)
            tried = await connection.test({})
            self.assertEqual(tried.state, ConnectionState.ERROR)
            self.assertIn("refused the token: invalid token", tried.detail)
            await connection.start()
            await self._settle()
            self.assertEqual(connection.status.state, ConnectionState.ERROR)
            self.assertEqual(len(server.subscriptions), 2)  # the test and one start: no asking in a loop
            self.assertNotIn("room", server.subscriptions[0])  # no account id in the file, none readable in the token
            await connection.stop()

    async def test_test_says_connected_without_keeping_the_line(self) -> None:
        self.token.write_text("my.jwt.token", encoding="utf-8")
        async with FakeAstroServer() as server:
            connection = self._connection(server, enabled=False)
            self.assertEqual((await connection.test({})).state, ConnectionState.CONNECTED)
            self.assertEqual(connection.status.state, ConnectionState.OFF)
            self.assertEqual(connection.fields(), [])  # the token is never typed into the tab


if __name__ == "__main__":
    unittest.main()
