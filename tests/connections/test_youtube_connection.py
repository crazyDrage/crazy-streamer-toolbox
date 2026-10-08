import asyncio
import socket
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.connections.youtube.youtube_events import youtube_events
from streamer_toolbox.connections.youtube_connection import YouTubeConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from tests.fakes.fake_youtube import READ, WRITE, FakeYouTube

BROADCAST = {"id": "vid1", "snippet": {"title": "Lizards", "liveChatId": "chat1"}}
KIT = {"channelId": "UC2", "displayName": "Kit", "isChatOwner": False, "isChatModerator": True,
       "isChatSponsor": True}


def message(kind: str, author: dict | None = None, message_id: str = "m1", **details) -> dict:
    """A liveChatMessage the way YouTube's reference describes it."""
    return {"kind": "youtube#liveChatMessage", "id": message_id, "snippet": {"type": kind, **details},
            "authorDetails": author or {"channelId": "UC3", "displayName": "Ann"}}


TEXT = message("textMessageEvent", KIT, textMessageDetails={"messageText": "!lizard two times"})
SUPERCHAT = message("superChatEvent", message_id="m2", superChatDetails={
    "amountMicros": "5000000", "currency": "eur", "amountDisplayString": "€5.00", "userComment": "for snacks",
    "tier": 2})


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestYouTubeConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = OAuthTokenStore(Path(self.tmp.name) / "youtube_token.json")
        self.youtube = FakeYouTube()
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []

        async def record(kind, data):
            self.seen.append((kind, data))

        self.events.subscribe(record)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def connection(self, **settings) -> YouTubeConnection:
        connection = YouTubeConnection({"enabled": True, "client_id": "cid", "client_secret": "secret", **settings},
                                       self.store, self.events, self.youtube.transport, login_timeout=5, look=0.05)
        connection._every = lambda: 0.02  # the test doesn't wait YouTube's seconds
        return connection

    def save_token(self, scopes: tuple[str, ...] = (READ,), expires_in: float = 3600) -> None:
        self.store.save(OAuthToken("access-1", "refresh-1", time.time() + expires_in, scopes, "UC1", "crazyDrage"))

    def test_a_chat_message_and_what_else_comes_through_the_chat(self) -> None:
        self.assertEqual(youtube_events(TEXT), [("youtube.chat", {
            "user": "Kit", "message": "!lizard two times", "command": "!lizard", "args": "two times", "role": "mod",
            "user_id": "UC2", "message_id": "m1", "platform": "youtube"})])
        money = {"user": "Ann", "amount": 5, "currency": "EUR", "message": "for snacks", "platform": "youtube"}
        self.assertEqual(youtube_events(SUPERCHAT), [("youtube.superchat", money), ("tip", money)])
        sticker = youtube_events(message("superStickerEvent", superStickerDetails={
            "superStickerMetadata": {"stickerId": "s", "altText": "a lizard waving"}, "amountMicros": 1990000,
            "currency": "USD"}))
        self.assertEqual([(kind, data["amount"], data["message"]) for kind, data in sticker],
                         [("youtube.supersticker", 1.99, "a lizard waving"), ("tip", 1.99, "a lizard waving")])
        events = [*youtube_events(TEXT), *youtube_events(SUPERCHAT), *sticker, *youtube_events(message(
            "newSponsorEvent", newSponsorDetails={"memberLevelName": "Lizard", "isUpgrade": False})),
            *youtube_events(message("memberMilestoneChatEvent", memberMilestoneChatDetails={
                "userComment": "a year!", "memberMonth": 12, "memberLevelName": "Lizard"})),
            *youtube_events(message("membershipGiftingEvent", membershipGiftingDetails={
                "giftMembershipsCount": 5, "giftMembershipsLevelName": "Lizard"}))]
        self.assertEqual(events[-3:], [
            ("youtube.member", {"user": "Ann", "level": "Lizard", "upgrade": False, "platform": "youtube"}),
            ("youtube.member_milestone", {"user": "Ann", "months": 12, "level": "Lizard", "message": "a year!",
                                          "platform": "youtube"}),
            ("youtube.gift_members", {"user": "Ann", "amount": 5, "level": "Lizard", "platform": "youtube"})])
        for kind, data in events:
            self.assertEqual(set(data), set(EVENT_FIELDS[kind]))  # what the Start box offers is what comes
        for kind in ("tombstone", "userBannedEvent", "giftMembershipReceivedEvent", "chatEndedEvent"):
            self.assertEqual(youtube_events(message(kind)), [])
        self.assertEqual(youtube_events({"snippet": "broken"}), [])

    async def test_it_is_off_until_switched_on_and_start_never_opens_a_browser(self) -> None:
        self.assertFalse(YouTubeConnection({}, self.store, self.events).settings["enabled"])
        connection = self.connection()
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.ERROR)
        self.assertIn("press Connect", connection.status.detail)
        self.assertEqual(self.youtube.calls, [])

    async def test_waits_for_a_stream_then_passes_the_chat_on_until_it_ends(self) -> None:
        self.save_token()
        connection = self.connection()
        await connection.start()
        await until(lambda: ("Chat", "waiting for a stream") in connection.status.facts)
        self.assertEqual(self.seen, [])
        old = message("textMessageEvent", message_id="m0", textMessageDetails={"messageText": "before"})
        self.youtube.pages = [
            {"items": [old], "nextPageToken": "p1", "pollingIntervalMillis": 10},  # the history: not news
            {"items": [TEXT, SUPERCHAT], "nextPageToken": "p2", "pollingIntervalMillis": 10},
            {"items": [], "nextPageToken": "p3", "pollingIntervalMillis": 10},
            httpx.Response(403, json={"error": {"message": "The live chat is no longer live.",
                                                "errors": [{"reason": "liveChatEnded"}]}})]
        self.youtube.broadcast = BROADCAST
        await until(lambda: any(kind == "youtube.offline" for kind, _ in self.seen))
        self.youtube.broadcast = None
        await self.events.wait_idle()
        self.assertEqual([kind for kind, _ in self.seen][:5], [
            "youtube.online", "youtube.chat", "youtube.superchat", "tip", "youtube.offline"])
        self.assertEqual(self.seen[0][1], {"title": "Lizards", "platform": "youtube"})
        asked = [params.get("pageToken", "") for method, name, params in self.youtube.calls
                 if (method, name) == ("GET", "liveChat/messages")]
        self.assertEqual(asked[:4], ["", "p1", "p2", "p3"])  # each ask continues where the last ended
        await connection.stop()
        self.assertEqual(connection.status.state, ConnectionState.OFF)

    async def test_an_expired_login_is_renewed_and_keeps_who_it_is(self) -> None:
        self.save_token(expires_in=10)
        connection = self.connection()
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.CONNECTED, connection.status.detail)
        saved = self.store.load()
        self.assertEqual((saved.access_token, saved.refresh_token, saved.login, saved.scopes),
                         ("access-2", "refresh-1", "crazyDrage", (READ,)))
        await connection.stop()
        self.save_token(expires_in=10)
        self.youtube.refresh_ok = False
        await connection.start()
        self.assertEqual(connection.status.state, ConnectionState.ERROR)
        self.assertIn("press Connect", connection.status.detail)

    async def test_a_used_up_quota_is_told_and_waited_out(self) -> None:
        self.save_token()
        self.youtube.broadcast = BROADCAST
        self.youtube.pages = [httpx.Response(403, json={"error": {"message": "quota", "errors": [
            {"reason": "quotaExceeded"}]}})]
        connection = self.connection()
        await connection.start()
        await until(lambda: connection.status.state is ConnectionState.ERROR)
        self.assertIn("quota is used up", connection.status.detail)
        asked = len(self.youtube.calls)
        await asyncio.sleep(0.2)
        self.assertEqual(len(self.youtube.calls), asked)  # no asking in a loop
        await connection.stop()

    async def test_a_channel_without_live_streaming_is_told_plainly_and_isnt_a_login_problem(self) -> None:
        self.save_token()
        self.youtube.not_enabled = True
        connection = self.connection()
        await connection.start()
        await until(lambda: connection.status.state is ConnectionState.ERROR)
        self.assertIn("live streaming isn't switched on", connection.status.detail)
        self.assertNotIn("press Connect", connection.status.detail)
        asked = len(self.youtube.calls)
        await asyncio.sleep(0.2)
        self.assertEqual(len(self.youtube.calls), asked)  # no asking in a loop
        await connection.stop()

    async def test_connect_logs_in_through_the_browser_and_asks_only_to_read(self) -> None:
        port = free_port()
        opened = []

        def browser(url: str) -> None:  # stands in for the streamer allowing the app
            opened.append(url)
            state = parse_qs(urlsplit(url).query)["state"][0]
            asyncio.get_running_loop().create_task(visit(f"http://localhost:{port}/?code=the-code&state={state}"))

        async def visit(url: str) -> None:
            async with httpx.AsyncClient() as client:
                await client.get(url)

        connection = YouTubeConnection({}, self.store, self.events, self.youtube.transport, open_browser=browser,
                                       login_timeout=5)
        settings = {"client_id": "cid", "client_secret": "secret", "redirect_url": f"http://localhost:{port}"}
        self.assertEqual((await connection.test({})).state, ConnectionState.ERROR)
        status = await connection.test(settings)
        self.assertEqual((status.state, status.facts), (ConnectionState.CONNECTED, (("Channel", "crazyDrage"),)),
                         status.detail)
        query = parse_qs(urlsplit(opened[0]).query)
        self.assertEqual((query["scope"], query["access_type"]), ([READ], ["offline"]))
        saved = self.store.load()
        self.assertEqual((saved.access_token, saved.refresh_token, saved.user_id), ("access-2", "refresh-2", "UC1"))
        # "May write in chat" switched on: the read-only login isn't enough, Connect asks for the bigger permission
        self.youtube.scope = f"{READ} {WRITE}"
        status = await connection.test({**settings, "may_write": "yes"})
        self.assertEqual(status.state, ConnectionState.CONNECTED, status.detail)
        self.assertEqual(parse_qs(urlsplit(opened[1]).query)["scope"], [f"{READ} {WRITE}"])
        self.assertEqual(self.store.load().scopes, (READ, WRITE))

    async def test_send_chat_needs_his_switch_and_a_live_stream(self) -> None:
        self.save_token()
        self.youtube.broadcast = BROADCAST
        connection = self.connection()
        await connection.start()
        await until(lambda: ("Chat", "listening") in connection.status.facts)
        with self.assertRaises(PermissionError):  # a read-only login
            await connection.send_chat("hi")
        await connection.stop()
        with self.assertRaises(NotConnectedError):
            await connection.send_chat("hi")
        self.save_token((READ, WRITE))
        self.youtube.broadcast = None
        connection = self.connection(may_write="yes")
        await connection.start()
        await until(lambda: ("Chat", "waiting for a stream") in connection.status.facts)
        with self.assertRaises(NotConnectedError):  # not live: no chat to write in
            await connection.send_chat("hi")
        self.youtube.broadcast = BROADCAST
        await until(lambda: ("Chat", "listening") in connection.status.facts)
        await connection.send_chat("hello chat")
        self.assertEqual(self.youtube.sent, [{"snippet": {
            "liveChatId": "chat1", "type": "textMessageEvent", "textMessageDetails": {"messageText": "hello chat"}}}])
        self.assertIn(("May write", "yes"), connection.status.facts)
        await connection.stop()


if __name__ == "__main__":
    unittest.main()
