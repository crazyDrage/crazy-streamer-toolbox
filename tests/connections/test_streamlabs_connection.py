import asyncio
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.streamlabs.streamlabs_events import ACTIVITY, streamlabs_events
from streamer_toolbox.connections.streamlabs_connection import StreamlabsConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_streamlabs_server import FakeStreamlabsServer

# real events of the socket (2026-10-03, the Alert Box's test buttons), ids shortened
DONATION = {"type": "donation", "message": [{
    "name": "streamer", "message": "This is a test donation for $23.00", "from": "Kevin", "to": {"name": "streamer"},
    "from_user_id": 1, "amount": 23, "formattedAmount": "$23.00", "currency": "USD", "recurring": False,
    "isTest": True, "isPreview": False, "unsavedSettings": [], "freeze": False, "_id": "3b12", "priority": 10}],
    "for": "streamlabs", "event_id": "evt_d5fa"}
RAID = {"type": "raid", "message": [{"name": "goodwin", "raiders": 7248, "viewers": 7248, "isTest": True,
                                     "isPreview": False, "_id": "a0bc", "priority": 10}],
        "for": "twitch_account", "event_id": "evt_fe7a"}
MERCH = {"type": "merch", "message": [{"name": "streamer", "message": "This is a test merch purchase",
                                       "from": "John", "product": "T-Shirt", "isTest": True, "isPreview": False}],
         "for": "streamlabs", "event_id": "evt_d62a"}
SUPERCHAT = {"type": "superchat", "message": [{
    "id": "55761", "name": "Kevin", "channelId": "UC1", "comment": "This is a test superchat message!",
    "amount": 6000000, "currency": "USD", "displayString": "$6.00", "isTest": True, "isPreview": False}],
    "for": "youtube_account", "event_id": "evt_9d0b"}
JEWELS = {"type": "jewelGift", "message": [{"name": "Kevin", "giftName": "Thumbs up", "jewelsAmount": 10,
                                            "message": "Thumbs up gift", "isTest": True}],
          "for": "youtube_account", "event_id": "evt_9908"}
PREVIEW_FOLLOW = {"type": "follow", "message": [{"name": "Kevin", "isTest": False, "isPreview": True}],
                  "for": "twitch_account"}


class TestStreamlabsConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.token = Path(self._dir.name) / "streamlabs_token.txt"
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def listen(kind: str, data: dict) -> None:
            self.seen.append((kind, data))

        self.events.subscribe(listen)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _connection(self, server: FakeStreamlabsServer) -> StreamlabsConnection:
        return StreamlabsConnection({"enabled": True}, self.token, self.events, url=server.url)

    async def _settle(self, seconds: float = 0.3) -> None:
        await asyncio.sleep(seconds)
        await self.events.wait_idle()

    def test_a_donation_is_an_activity_and_the_toolboxes_tip(self) -> None:
        events = streamlabs_events(DONATION)
        self.assertEqual(events, [
            (ACTIVITY, {"type": "donation", "user": "Kevin", "amount": 23, "currency": "USD",
                        "message": "This is a test donation for $23.00", "product": "", "test": True,
                        "platform": "streamlabs"}),
            ("tip", {"user": "Kevin", "amount": 23, "currency": "USD",
                     "message": "This is a test donation for $23.00", "platform": "streamlabs"})])
        for kind, data in events:
            self.assertEqual(set(data), set(EVENT_FIELDS[kind]))  # what the Start box offers is what comes

    def test_youtube_comes_through_the_same_line(self) -> None:
        activity, tip = streamlabs_events(SUPERCHAT)
        self.assertEqual(activity, (ACTIVITY, {
            "type": "superchat", "user": "Kevin", "amount": 6, "currency": "USD",
            "message": "This is a test superchat message!", "product": "", "test": True, "platform": "youtube"}))
        self.assertEqual(tip, ("tip", {"user": "Kevin", "amount": 6, "currency": "USD",
                                       "message": "This is a test superchat message!", "platform": "youtube"}))
        sticker = {"type": "superSticker", "message": [{"name": "Kevin", "amount": 46500000, "currency": "USD"}],
                   "for": "youtube_account"}
        self.assertEqual(streamlabs_events(sticker)[1][1]["amount"], 46.5)
        gift = streamlabs_events(JEWELS)
        self.assertEqual((len(gift), gift[0][1]["amount"], gift[0][1]["platform"]), (1, 10, "youtube"))  # no tip

    def test_other_activities_and_their_housekeeping(self) -> None:
        self.assertEqual(streamlabs_events(RAID), [(ACTIVITY, {
            "type": "raid", "user": "goodwin", "amount": 7248, "currency": "", "message": "", "product": "",
            "test": True, "platform": "twitch"})])
        merch = streamlabs_events(MERCH)[0][1]
        self.assertEqual((merch["user"], merch["product"], merch["amount"]), ("John", "T-Shirt", 0))
        self.assertTrue(streamlabs_events(PREVIEW_FOLLOW)[0][1]["test"])  # a preview from their editor
        text_amount = {"type": "donation", "message": [{"name": "Kit", "amount": "13.37", "currency": "eur"}]}
        self.assertEqual(streamlabs_events(text_amount)[1][1], {
            "user": "Kit", "amount": 13.37, "currency": "EUR", "message": "", "platform": "streamlabs"})
        for kind in ("alertPlaying", "streamlabels", "streamlabels.underlying", "subscription-playing"):
            self.assertEqual(streamlabs_events({"type": kind, "message": {"from": "Kevin"}}), [])
        self.assertEqual(streamlabs_events({"type": "donation", "message": "not a list"}), [])

    async def test_it_is_off_until_switched_on_and_needs_the_token_file(self) -> None:
        async with FakeStreamlabsServer() as server:
            self.assertFalse(StreamlabsConnection({}, self.token, self.events, url=server.url).settings["enabled"])
            connection = self._connection(server)
            await connection.start()
            self.assertEqual(connection.status.state, ConnectionState.ERROR)
            self.assertIn("No token yet", connection.status.detail)
            self.assertEqual((server.connections, connection.fields()), (0, []))

    async def test_listens_with_the_token_answers_pings_and_passes_events_on(self) -> None:
        self.token.write_text("socket-token\n", encoding="utf-8")
        async with FakeStreamlabsServer() as server:
            connection = self._connection(server)
            await connection.start()
            await asyncio.wait_for(server.connected.wait(), 5)
            await self._settle()
            self.assertEqual(connection.status.state, ConnectionState.CONNECTED)
            self.assertEqual(server.tokens, ["socket-token"])
            self.assertGreaterEqual(server.pings, 2)  # the line is kept alive
            await server.event(DONATION)
            await server.event(DONATION)  # the same event id again
            await server.event({"type": "alertPlaying", "message": {"from": "Kevin"}})
            await server.event(MERCH, name="something_else")
            await self._settle()
            self.assertEqual([(kind, data.get("type", "")) for kind, data in self.seen],
                             [(ACTIVITY, "donation"), ("tip", "")])
            await connection.stop()
            self.assertEqual(connection.status.state, ConnectionState.OFF)

    async def test_a_line_that_goes_quiet_is_opened_again(self) -> None:
        self.token.write_text("socket-token", encoding="utf-8")
        async with FakeStreamlabsServer() as server:
            server.answer_pings = False
            connection = StreamlabsConnection({"enabled": True}, self.token, self.events, url=server.url)
            await connection.start()
            for _ in range(100):  # no answer within the ping timeout: it gives up on that line
                await asyncio.sleep(0.05)
                if connection.status.state is ConnectionState.ERROR:
                    break
            self.assertIn("no answer to our ping", connection.status.detail)
            self.assertNotIn("socket-token", connection.status.detail)
            await connection.stop()

    async def test_a_refused_token_shows_on_the_tab_and_isnt_asked_again(self) -> None:
        self.token.write_text("old-token", encoding="utf-8")
        async with FakeStreamlabsServer(accept=False) as server:
            connection = self._connection(server)
            tried = await connection.test({})
            self.assertEqual(tried.state, ConnectionState.ERROR)
            self.assertIn("refused the token", tried.detail)
            await connection.start()
            await self._settle()
            self.assertEqual(connection.status.state, ConnectionState.ERROR)
            self.assertEqual(server.connections, 2)  # the test and one start: no asking in a loop
            await connection.stop()


if __name__ == "__main__":
    unittest.main()
