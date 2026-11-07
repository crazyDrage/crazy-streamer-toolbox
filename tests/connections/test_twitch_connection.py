import asyncio
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.connections.twitch.twitch_reward import TwitchReward
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.oauth.account_tokens import AccountTokens
from streamer_toolbox.connections.twitch_connection import TwitchConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.current_account import ACCOUNT
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.flows.flow_trigger import REWARDS
from tests.fakes.fake_eventsub_server import FakeEventSubServer
from tests.fakes.fake_twitch import SCOPES, FakeTwitch
from streamer_toolbox.connections.twitch.twitch_auth import BOT_SCOPES, BUILT_IN_CLIENT_ID, EXTRA_SCOPES

REDEMPTION = "channel.channel_points_custom_reward_redemption.add"
EVENT = {"id": "red1", "user_login": "vexfan", "user_name": "VexFan", "user_input": "hi",
         "reward": {"id": "r1", "title": "Big Action: clean screen", "cost": 500}}


async def until(check, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while not check():
        if time.monotonic() > end:
            raise AssertionError("timed out")
        await asyncio.sleep(0.02)


class TestTwitchConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.main = {"name": ""}  # [twitch] main_account
        folder = Path(self.tmp.name) / "twitch"
        self.store = AccountTokens(folder, lambda file: folder / file, lambda: self.main["name"],
                                   lambda name: self.main.update(name=name))
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
        return TwitchConnection({"enabled": True, **settings},
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
                "platform": "twitch", "account": "crazydrage", "main_account": "crazydrage"}))
            await first.reconnect_to(second.url)
            await until(lambda: second.sessions == 1)
            await second.notify(REDEMPTION, {**EVENT, "user_name": "Kit"}, message_id="m2")
            await until(lambda: len(self.seen) == 2)
            await twitch.stop()
        self.assertEqual(self.seen[0], ("twitch.redeem", {
            "reward": "Big Action: clean screen", "reward_id": "r1", "cost": 500, "user": "VexFan",
            "user_login": "vexfan", "user_id": "", "input": "hi", "redemption_id": "red1", "platform": "twitch",
            "account": "crazydrage", "main_account": "crazydrage"}))
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

    async def test_connect_logs_in_again_when_the_saved_login_lacks_a_newer_permission(self) -> None:
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

    async def test_connect_logs_in_with_a_code_and_no_secret(self) -> None:
        self.twitch.device_asks_until_confirmed = 2
        opened = []
        twitch = TwitchConnection({"enabled": True}, self.store, self.events, self.twitch.transport, open_browser=opened.append,
                                  login_timeout=5, code_wait=0.01)
        status = await twitch.test(twitch.settings)  # the toolbox's own app, nothing to type
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

    async def test_a_code_nobody_confirms_and_a_login_of_another_app(self) -> None:
        self.twitch.device_asks_until_confirmed = 10_000
        twitch = TwitchConnection({"enabled": True}, self.store, self.events, self.twitch.transport, open_browser=lambda url: None,
                                  login_timeout=0.1, code_wait=0.02)
        status = await twitch.test(twitch.settings)
        self.assertEqual(status.state, ConnectionState.ERROR)
        self.assertIn("in time", status.detail)
        self.assertIsNone(self.store.load())
        # a login made with an app of his own (before 2026-11-05) isn't the toolbox's: Connect is asked for
        self.twitch.client_id = "his-own-app"
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

    async def test_the_follower_check_finds_missed_follows_and_each_follow_comes_once(self) -> None:
        """His failsafe of 2026-11-05: "sometimes twitch doesn't see new followers"."""
        def follower(user_id: str, name: str) -> dict:
            return {"user_id": user_id, "user_login": name.casefold(), "user_name": name,
                    "followed_at": "2026-11-06T10:00:00Z"}

        def follows() -> list[str]:
            return [data["user"] for kind, data in self.seen if kind == "twitch.follow"]

        def asked() -> int:
            return sum(r.url.path == "/helix/channels/followers" for r in self.twitch.requests)

        self.save_token()
        self.twitch.followers = [follower("1", "Ann")]
        with patch("streamer_toolbox.core.followers.follower_check.FASTEST", 0.01):
            async with FakeEventSubServer() as server:
                twitch = self.connection(server.url, follower_check="0.01")
                await twitch.start()
                await until(lambda: dict(twitch.status.facts).get("Events") == "listening" and asked() >= 1)
                await server.notify("channel.follow", {"user_id": "2", "user_login": "bee", "user_name": "Bee",
                                                       "followed_at": "x"}, message_id="f1")
                await until(lambda: follows() == ["Bee"])
                self.twitch.followers = [follower("3", "Cat"), follower("2", "Bee"), follower("1", "Ann")]
                await until(lambda: follows() == ["Bee", "Cat"])  # Twitch's live event missed Cat
                await server.notify("channel.follow", {"user_id": "3", "user_login": "cat", "user_name": "Cat",
                                                       "followed_at": "x"}, message_id="f2")
                await until(lambda: asked() >= 5)
                await twitch.stop()
        self.assertEqual(follows(), ["Bee", "Cat"])  # Ann followed before: not news; Cat only once
        self.assertEqual(next(d for k, d in self.seen if d.get("user") == "Cat"), {
            "user": "Cat", "user_login": "cat", "user_id": "3", "followed_at": "2026-11-06T10:00:00Z",
            "platform": "twitch", "account": "crazydrage", "main_account": "crazydrage"})

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
        topic = {"title": "Lizard time", "category": "Just Chatting", "platform": "twitch", "account": "crazydrage",
                 "main_account": "crazydrage"}
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
                                                     "viewers": 12, "platform": "twitch", "account": "crazydrage",
                                                     "main_account": "crazydrage"})])
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

    async def _with_bot(self) -> TwitchConnection:
        """His channel crazydrage (main, logged in with Connect) plus the bot account crazydrage_bot."""
        self.save_token()
        twitch = self.connection()
        await twitch.start()
        self.twitch.next_login = ("crazydrage_bot", "77")
        shown: list[tuple[str, str]] = []
        opened = []
        twitch._open_browser = opened.append
        name = await twitch.add_account(True, lambda page, code: shown.append((page, code)))
        self.assertEqual(name, "crazydrage_bot")
        self.assertEqual(shown, [("https://www.twitch.tv/activate?device-code=ABCDEFGH", "ABCDEFGH")])
        self.assertEqual(opened, [])  # the link is for another browser: nothing opens on this PC
        return twitch

    async def test_an_added_bot_account_asks_only_for_the_bot_permissions(self) -> None:
        twitch = await self._with_bot()
        self.assertEqual(self.twitch.device_scopes.split(), list(BOT_SCOPES))
        self.assertEqual((twitch.account_names(), twitch.main_account()), (["crazydrage", "crazydrage_bot"],
                                                                          "crazydrage"))
        self.assertTrue(twitch.is_bot("crazydrage_bot"))
        self.assertEqual(twitch.account_state("crazydrage_bot"), "connected")
        self.assertIn(("Other accounts", "crazydrage_bot"), twitch.status.facts)
        await twitch.stop()

    async def test_the_bot_writes_and_moderates_in_his_channel(self) -> None:
        twitch = await self._with_bot()
        actions = ActionRegistry()
        twitch.add_actions(actions)
        self.twitch.scopes = SCOPES + list(EXTRA_SCOPES)
        await twitch.stop()
        await twitch.start()  # both logins again, now with every permission
        mark = ACCOUNT.set("crazydrage_bot")
        try:
            await actions.run("twitch.send_chat", message="beep")
        finally:
            ACCOUNT.reset(mark)
        await actions.run("twitch.send_chat", message="from me")  # nothing set: the main account
        self.assertEqual([(c["broadcaster_id"], c["sender_id"], c["message"]) for c in self.twitch.chat],
                         [("42", "77", "beep"), ("42", "42", "from me")])
        await twitch.stop()

    async def test_an_account_that_is_gone_says_so(self) -> None:
        twitch = await self._with_bot()
        actions = ActionRegistry()
        twitch.add_actions(actions)
        await twitch.remove_account("crazydrage_bot")
        self.assertEqual(twitch.account_names(), ["crazydrage"])
        self.assertFalse(twitch.is_bot("crazydrage_bot"))
        mark = ACCOUNT.set("crazydrage_bot")
        try:
            with self.assertRaisesRegex(Exception, "no account 'crazydrage_bot'"):
                await actions.run("twitch.send_chat", message="beep")
        finally:
            ACCOUNT.reset(mark)
        await twitch.stop()

    async def test_a_second_channel_that_listens_says_which_account_heard_it(self) -> None:
        """His answer 120: another account's own channel, switched on; every event says its account."""
        self.save_token()
        async with FakeEventSubServer() as server:
            twitch = self.connection(server.url)
            await twitch.start()
            self.twitch.next_login = ("second_channel", "77")
            await twitch.add_account(False, lambda page, code: None)
            await twitch.set_listening("second_channel", True)  # starts again with both listening
            self.assertEqual(twitch.listening_accounts(), ["crazydrage", "second_channel"])
            await until(lambda: server.sessions == 2)
            await until(lambda: {s["condition"].get("broadcaster_user_id") for s in self.twitch.subscriptions}
                        >= {"42", "77"})
            await server.notify_all(REDEMPTION, EVENT)
            await until(lambda: len(self.seen) == 2)
            await twitch.stop()
        self.assertEqual(sorted(data["account"] for _, data in self.seen), ["crazydrage", "second_channel"])

    async def test_a_bot_account_never_listens(self) -> None:
        twitch = await self._with_bot()
        await twitch.set_listening("crazydrage_bot", True)
        self.assertEqual(twitch.listening_accounts(), ["crazydrage"])
        await twitch.stop()

    async def test_another_main_account_restarts_on_it(self) -> None:
        twitch = await self._with_bot()
        self.twitch.scopes = SCOPES + list(EXTRA_SCOPES)
        await twitch.set_listening("crazydrage_bot", True)
        self.assertTrue(twitch.listens("crazydrage_bot"))
        await twitch.set_main_account("crazydrage_bot")
        self.assertEqual(self.main["name"], "crazydrage_bot")
        self.assertEqual(dict(twitch.status.facts)["Account"], "crazydrage_bot")
        await twitch.stop()

    async def test_the_chat_reward_and_marker_boxes_reach_twitch(self) -> None:
        """The Box classes run by name, as a flow runs them (the connection's methods are tested above)."""
        self.save_token()
        twitch = self.connection()
        actions = ActionRegistry()
        twitch.add_actions(actions)
        await twitch.start()
        await actions.run("twitch.send_chat", message="hello chat")
        made = await actions.run("twitch.create_reward", title="Hydrate", cost=50, prompt="drink", needs_text=True)
        await actions.run("twitch.set_reward_paused", reward=made, paused=True)
        await actions.run("twitch.set_reward_enabled", reward="hydrate", enabled=False)
        rewards = await actions.run("twitch.rewards")
        await actions.run("twitch.finish_redeem", reward_id=made, redemption_id="red1", refund=True)
        marker = await actions.run("twitch.create_marker", description="clip this")
        await twitch.stop()
        self.assertEqual([c["message"] for c in self.twitch.chat], ["hello chat"])
        reward = next(r for r in self.twitch.rewards if r["id"] == made)
        self.assertEqual((reward["title"], reward["cost"], reward["prompt"], reward["is_user_input_required"]),
                         ("Hydrate", 50, "drink", True))
        self.assertEqual(self.twitch.updates, [(made, {"is_paused": True}), (made, {"is_enabled": False})])
        self.assertIn(("Hydrate", True), [(r["title"], r["by_toolbox"]) for r in rewards])
        self.assertEqual([(p["reward_id"], p["id"], b["status"]) for p, b in self.twitch.redemptions],
                         [(made, "red1", "CANCELED")])
        self.assertEqual((marker, self.twitch.markers[-1]["description"]), ("mk1", "clip this"))


if __name__ == "__main__":
    unittest.main()
