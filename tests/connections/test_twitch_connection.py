import asyncio
import socket
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.connections.twitch.twitch_reward import TwitchReward
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.connections.twitch_connection import TwitchConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.flows.flow_trigger import REWARDS
from tests.fakes.fake_eventsub_server import FakeEventSubServer
from tests.fakes.fake_twitch import SCOPES, FakeTwitch
from streamer_toolbox.connections.twitch.twitch_auth import BUILT_IN_CLIENT_ID, EXTRA_SCOPES

REDEMPTION = "channel.channel_points_custom_reward_redemption.add"
EVENT = {"id": "red1", "user_login": "vexfan", "user_name": "VexFan", "user_input": "hi",
         "reward": {"id": "r1", "title": "Big Action: clean screen", "cost": 500}}


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


class TestTwitchConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = OAuthTokenStore(Path(self.tmp.name) / "twitch_token.json")
        self.twitch = FakeTwitch()
        self.events = EventBus()
        self.seen: list[tuple[str, dict]] = []
        self.raw: list[tuple[str, dict]] = []  # Twitch's own message of each event
        self.reward_lists: list[dict] = []  # the reward list it announces when it connects (kept apart)

        async def record(kind, data):
            if kind == REWARDS:
                self.reward_lists.append(data)
            else:
                self.seen.append((kind, data))

        self.events.subscribe(record)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def connection(self, url: str = "ws://127.0.0.1:9", **settings) -> TwitchConnection:
        return TwitchConnection({"enabled": True, "client_id": "cid", "client_secret": "secret", **settings},
                                self.store, self.events,
                                self.twitch.transport, eventsub_url=url, login_timeout=5,
                                raw=lambda kind, message: self.raw.append((kind, message)))

    def save_token(self, access: str = "access-1", expires_in: float = 3600) -> None:
        self.store.save(OAuthToken(access, "refresh-1", time.time() + expires_in, tuple(SCOPES)))

    async def test_start_without_login_asks_for_connect(self) -> None:
        twitch = self.connection()
        await twitch.start()
        self.assertEqual(twitch.status.state, ConnectionState.ERROR)
        self.assertIn("press Connect", twitch.status.detail)

    async def test_redeem_becomes_an_event_and_reconnect_keeps_listening(self) -> None:
        self.save_token()
        async with FakeEventSubServer() as first, FakeEventSubServer() as second:
            twitch = self.connection(first.url)
            await twitch.start()
            await until(lambda: self.twitch.subscriptions)
            self.assertEqual(self.twitch.subscriptions[0]["transport"], {"method": "websocket",
                                                                        "session_id": "session-1"})
            self.assertEqual(self.twitch.subscriptions[0]["condition"], {"broadcaster_user_id": "42"})
            await until(lambda: dict(twitch.status.facts).get("Events") == "listening")
            self.assertEqual(dict(twitch.status.facts)["Account"], "crazydrage")
            await until(lambda: self.reward_lists)  # connected: the rewards as they are now, to update triggers
            self.assertIn({"id": "r1", "title": self.twitch.rewards[0]["title"]}, self.reward_lists[0]["rewards"])

            await first.notify(REDEMPTION, EVENT)
            await first.notify(REDEMPTION, EVENT)  # same message id twice: only one event
            await until(lambda: self.seen)
            await first.notify("channel.chat.message", {  # shared chat: from the other channel, left out
                "broadcaster_user_id": "42", "source_broadcaster_user_id": "77", "chatter_user_name": "Guest",
                "message_id": "c0", "message": {"text": "lizard"}}, message_id="m-shared")
            await first.notify("channel.chat.message", {"chatter_user_name": "Kit", "chatter_user_login": "kit",
                                                        "message_id": "c1", "message": {"text": " !QA how are you? "}},
                               message_id="m-chat")
            await until(lambda: len(self.seen) == 2)
            self.assertEqual(self.seen.pop(), ("twitch.chat", {
                "message": "!QA how are you?", "command": "!qa", "args": "how are you?", "user": "Kit",
                "user_login": "kit", "message_id": "c1", "role": "viewer", "user_id": "", "color": "", "emotes": [],
                "platform": "twitch"}))
            await first.reconnect_to(second.url)
            await until(lambda: second.sessions == 1)
            await second.notify(REDEMPTION, {**EVENT, "user_name": "Kit"}, message_id="m2")
            await until(lambda: len(self.seen) == 2)
            await twitch.stop()
        self.assertEqual(self.seen[0], ("twitch.redeem", {
            "reward": "Big Action: clean screen", "reward_id": "r1", "cost": 500, "user": "VexFan",
            "user_login": "vexfan", "user_id": "", "input": "hi", "redemption_id": "red1", "platform": "twitch"}))
        self.assertEqual(self.seen[1][1]["user"], "Kit")
        self.assertEqual(self.seen[0][1]["user"], "VexFan")
        types = [s["type"] for s in self.twitch.subscriptions]
        self.assertEqual(types[:2], [REDEMPTION, "channel.chat.message"])
        self.assertEqual(len(types), 16)  # 16 kinds; a reconnect keeps them (no new ones)
        self.assertEqual(self.twitch.subscriptions[1]["condition"], {"broadcaster_user_id": "42", "user_id": "42"})

    async def test_expired_token_is_renewed_and_saved(self) -> None:
        self.save_token(expires_in=-10)
        twitch = self.connection()
        await twitch.start()
        await twitch.stop()
        self.assertEqual(self.store.load().access_token, "access-2")
        self.assertEqual(self.store.load().user_id, "42")

    async def test_dead_login_that_cant_be_renewed_asks_for_connect(self) -> None:
        self.save_token(access="revoked")
        self.twitch.refresh_ok = False
        twitch = self.connection()
        await twitch.start()
        self.assertEqual(twitch.status.state, ConnectionState.ERROR)
        self.assertIn("press Connect", twitch.status.detail)

    async def test_connect_logs_in_through_the_browser(self) -> None:
        port = free_port()
        opened = []

        def browser(url: str) -> None:  # stands in for the streamer clicking "Authorize"
            opened.append(url)
            state = parse_qs(urlsplit(url).query)["state"][0]
            asyncio.get_running_loop().create_task(visit(f"http://localhost:{port}/?code=the-code&state={state}"))

        async def visit(url: str) -> None:
            async with httpx.AsyncClient() as client:
                await client.get(url)

        twitch = TwitchConnection({"enabled": True}, self.store, self.events, self.twitch.transport, open_browser=browser,
                                  login_timeout=5)
        status = await twitch.test({"client_id": "cid", "client_secret": "secret",
                                    "redirect_url": f"http://localhost:{port}"})
        self.assertEqual(status.state, ConnectionState.CONNECTED, status.detail)
        self.assertEqual(status.facts, (("Account", "crazydrage"),))
        query = parse_qs(urlsplit(opened[0]).query)
        self.assertEqual(query["scope"][0].split(), SCOPES + list(EXTRA_SCOPES))  # the extra ones are asked for
        # ... and a login without them (the fake grants only the basic ones) still connects
        self.assertEqual(self.store.load().access_token, "access-2")

    async def test_connect_logs_in_again_when_the_saved_login_lacks_a_newer_permission(self) -> None:
        self.twitch.client_id = BUILT_IN_CLIENT_ID
        self.save_token()  # works, but from before the extra permissions
        opened = []
        twitch = TwitchConnection({"enabled": True}, self.store, self.events, self.twitch.transport,
                                  open_browser=opened.append, login_timeout=5, code_wait=0.01)
        status = await twitch.test(twitch.settings)
        self.assertEqual(status.state, ConnectionState.CONNECTED, status.detail)
        self.assertEqual(len(opened), 1)
        self.assertEqual(self.store.load().access_token, "access-2")  # the new login is the saved one
        self.twitch.scopes = SCOPES + list(EXTRA_SCOPES)  # a login that has everything: no page opens
        await twitch.test(twitch.settings)
        self.assertEqual(len(opened), 1)

    async def test_without_an_own_app_connect_logs_in_with_a_code_and_no_secret(self) -> None:
        self.twitch.client_id = BUILT_IN_CLIENT_ID
        self.twitch.device_asks_until_confirmed = 2
        opened = []
        twitch = TwitchConnection({"enabled": True}, self.store, self.events, self.twitch.transport, open_browser=opened.append,
                                  login_timeout=5, code_wait=0.01)
        status = await twitch.test(twitch.settings)  # nothing typed: the toolbox's own app
        self.assertEqual(status.state, ConnectionState.CONNECTED, status.detail)
        self.assertEqual(opened, ["https://www.twitch.tv/activate?device-code=ABCDEFGH"])
        self.assertEqual(self.twitch.device_scopes.split(), SCOPES + list(EXTRA_SCOPES))
        forms = [parse_qs(r.content.decode()) for r in self.twitch.requests if r.url.path.startswith("/oauth2/")
                 and r.method == "POST"]
        self.assertEqual(len(forms), 4)  # the code, two "not yet", the tokens
        for form in forms:
            self.assertEqual(form["client_id"], [BUILT_IN_CLIENT_ID])
            self.assertNotIn("client_secret", form)
        self.assertEqual(self.store.load().login, "crazydrage")
        # the saved login is used and renewed without a secret; each renewal's new refresh token is kept
        self.store.save(replace(self.store.load(), expires_at=time.time() - 10))
        before = self.store.load().refresh_token
        await twitch.start()
        self.assertEqual(twitch.status.state, ConnectionState.CONNECTED, twitch.status.detail)
        renewal = parse_qs(self.twitch.requests[-2].content.decode())
        self.assertEqual((renewal["grant_type"], "client_secret" in renewal), (["refresh_token"], False))
        self.assertNotEqual(self.store.load().refresh_token, before)
        await twitch.send_chat("hi")
        self.assertEqual(self.twitch.requests[-1].headers["Client-Id"], BUILT_IN_CLIENT_ID)
        await twitch.stop()

    async def test_a_code_nobody_confirms_and_a_secret_without_its_id(self) -> None:
        self.twitch.device_asks_until_confirmed = 10_000
        twitch = TwitchConnection({"enabled": True}, self.store, self.events, self.twitch.transport, open_browser=lambda url: None,
                                  login_timeout=0.1, code_wait=0.02)
        status = await twitch.test(twitch.settings)
        self.assertEqual(status.state, ConnectionState.ERROR)
        self.assertIn("in time", status.detail)
        self.assertIsNone(self.store.load())
        status = await twitch.test({**twitch.settings, "client_secret": "secret"})
        self.assertIn("needs its Client ID", status.detail)
        # a login made with his own app isn't the built-in app's: Connect is asked for
        self.save_token()
        await twitch.start()
        self.assertIn("another Twitch app", twitch.status.detail)

    async def test_actions_retry_once_after_401(self) -> None:
        self.save_token()
        twitch = self.connection()
        await twitch.start()
        self.twitch.valid.discard("access-1")  # revoked behind our back
        self.twitch.rewards[0]["mine"] = True  # only a reward the toolbox made may be paused
        await twitch.send_chat("hello chat")
        await twitch.set_reward_paused("big action: CLEAN screen")
        await twitch.stop()
        self.assertEqual(self.twitch.chat, [{"broadcaster_id": "42", "sender_id": "42", "message": "hello chat"}])
        self.assertEqual(self.twitch.updates, [("r1", {"is_paused": True})])

    async def test_the_twitch_tool_lists_creates_changes_and_deletes_rewards(self) -> None:
        self.save_token()
        twitch = self.connection()
        await twitch.start()
        made = await twitch.save_reward(TwitchReward("Toolbox test", cost=1, paused=True, needs_text=True))
        self.assertTrue(made.id and made.by_toolbox and made.paused)
        rewards = {r.title: r for r in await twitch.list_rewards()}
        self.assertEqual((rewards["Big Action: clean screen"].by_toolbox, rewards["Toolbox test"].by_toolbox),
                         (False, True))
        changed = await twitch.save_reward(replace(made, title="Toolbox test 2", paused=False))
        self.assertEqual((changed.title, changed.paused), ("Toolbox test 2", False))
        with self.assertRaises(TwitchApiError):  # made on the dashboard: Twitch says no
            await twitch.delete_reward(rewards["Big Action: clean screen"].id)
        await twitch.delete_reward(made.id)
        self.assertEqual([r.title for r in await twitch.list_rewards()], ["Big Action: clean screen"])
        await twitch.stop()

    async def test_going_live_and_ending_say_the_title_and_the_category(self) -> None:
        self.save_token()
        async with FakeEventSubServer() as server:
            twitch = self.connection(server.url)
            await twitch.start()
            await until(lambda: dict(twitch.status.facts).get("Events") == "listening")
            await server.notify("stream.online", {"type": "live"}, message_id="on1")
            await server.notify("stream.offline", {}, message_id="off1")
            await until(lambda: len(self.seen) == 2)
            await twitch.stop()
        topic = {"title": "Lizard time", "category": "Just Chatting", "platform": "twitch"}
        self.assertEqual(self.seen, [("twitch.online", {"type": "live", **topic}), ("twitch.offline", topic)])

    async def test_refused_subscriptions_are_skipped_and_shown(self) -> None:
        self.save_token()
        self.twitch.refused = {"channel.subscribe", "channel.cheer"}
        async with FakeEventSubServer() as server:
            twitch = self.connection(server.url)
            await twitch.start()
            await until(lambda: dict(twitch.status.facts).get("Events") == "listening")
            await server.notify("channel.raid", {"from_broadcaster_user_name": "Vex", "from_broadcaster_user_login":
                                                 "vex", "from_broadcaster_user_id": "9", "viewers": 12},
                                message_id="r1")
            await until(lambda: self.seen)
            await twitch.stop()
        self.assertEqual(self.seen, [("twitch.raid", {"user": "Vex", "user_login": "vex", "user_id": "9",
                                                     "viewers": 12, "platform": "twitch"})])
        self.assertEqual(self.raw, [("twitch.raid", {  # as Twitch sent it, for the last trigger's file
            "from_broadcaster_user_name": "Vex", "from_broadcaster_user_login": "vex",
            "from_broadcaster_user_id": "9", "viewers": 12})])
        self.assertEqual(dict(twitch.status.facts).get("Not available", ""), "")  # stop() clears the status
        self.assertNotIn("channel.subscribe", [s["type"] for s in self.twitch.subscriptions])
        self.assertIn("stream.online", [s["type"] for s in self.twitch.subscriptions])

    async def test_reward_marker_and_redeem_actions(self) -> None:
        self.save_token()
        self.twitch.rewards.append({"id": "r2", "title": "Toolbox reward", "cost": 10, "mine": True})
        twitch = self.connection()
        await twitch.start()
        rewards = await twitch.rewards()
        await twitch.set_reward_enabled("toolbox REWARD", "false")
        await twitch.finish_redeem("r2", "red9", refund=True)
        await twitch.finish_redeem("r2", "red10")
        marker = await twitch.create_marker("lizard moment")
        await twitch.stop()
        self.assertEqual([(r["title"], r["by_toolbox"]) for r in rewards],
                         [("Big Action: clean screen", False), ("Toolbox reward", True)])
        self.assertEqual(self.twitch.updates, [("r2", {"is_enabled": False})])
        self.assertEqual([(p["id"], b["status"]) for p, b in self.twitch.redemptions],
                         [("red9", "CANCELED"), ("red10", "FULFILLED")])
        self.assertEqual((marker, self.twitch.markers), ("mk1", [{"user_id": "42", "description": "lizard moment"}]))


if __name__ == "__main__":
    unittest.main()
