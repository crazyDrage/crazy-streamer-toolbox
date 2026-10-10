import unittest
from datetime import datetime

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.twitch.twitch_auth import EXTRA_SCOPES, SCOPES
from streamer_toolbox.connections.twitch.twitch_role_list import TwitchRoleList
from streamer_toolbox.core.events.role_book import RoleBook
from streamer_toolbox.core.events.role_loader import RoleLoader
from streamer_toolbox.core.events.role_loading import CHAT, EVERY, START, RoleLoading
from tests.fakes.fake_helix import FakeHelix

ME = OAuthToken("a", "r", 0, tuple(SCOPES + EXTRA_SCOPES), "42", "streamer")


def users(*ids: str, cursor: str = "") -> dict:
    return {"data": [{"user_id": i, "user_login": f"user{i}"} for i in ids],
            "pagination": {"cursor": cursor} if cursor else {}}


def redeem(user_id: str) -> dict:
    return {"user": f"User{user_id}", "user_id": user_id, "reward": "Lizard", "platform": "twitch"}


class TestRoleLoader(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.time = 0.0
        self.helix = FakeHelix({
            ("GET", "subscriptions"): lambda p: users("8", cursor="next") if "after" not in p else users("7"),
            ("GET", "channels/vips"): users("9"), ("GET", "moderation/moderators"): users("7")})
        self.me: OAuthToken | None = ME
        self.book = RoleBook()
        self.setting = RoleLoading({})
        self.loader = RoleLoader(self.book, self.setting, TwitchRoleList(self.helix, lambda: self.me).read,
                                 now=lambda: self.time, clock=lambda: datetime(2026, 10, 10, 21, 5))

    def _role(self, user_id: str) -> str:
        return self.book.fill("twitch.redeem", redeem(user_id))["role"]

    async def test_the_lists_give_a_role_to_who_did_not_write_yet(self) -> None:
        self.assertTrue(await self.loader.load())
        self.assertEqual([self._role(i) for i in ("7", "8", "9", "5", "42")],
                         ["mod", "sub", "vip", "viewer", "broadcaster"])  # 7 is a sub too: the higher one counts
        self.assertEqual(self.loader.status, "Loaded at 21:05: 1 mods, 1 VIPs, 2 subs (4 requests).")
        self.assertEqual(self.helix.sent("GET", "subscriptions")[1][0],
                         {"broadcaster_id": "42", "first": 100, "after": "next"})
        self.book.fill("twitch.chat", {**redeem("9"), "role": "mod", "message": "hi"})  # chat knows better
        self.assertEqual(self._role("9"), "mod")
        self.helix.answers[("GET", "moderation/moderators")] = users()
        await self.loader.load()  # the next load: nobody is a mod anymore
        self.assertEqual([self._role(i) for i in ("7", "9")], ["sub", "vip"])

    async def test_when_a_load_is_due(self) -> None:
        self.assertEqual((self.setting.mode, self.loader.due()), (CHAT, False))  # only from chat: never
        self.setting.set_mode(START)
        self.assertTrue(self.loader.due())
        await self.loader.load()
        self.time = 100000.0
        self.assertFalse(self.loader.due())  # once is once
        self.setting.set_mode(EVERY)
        self.setting.set_minutes(5)
        self.time = await self._loaded_now()
        self.time += 299
        self.assertFalse(self.loader.due())
        self.time += 2
        self.assertTrue(self.loader.due())

    async def _loaded_now(self) -> float:
        await self.loader.load()
        return self.time

    async def test_a_failed_load_says_why_and_waits_before_the_next_try(self) -> None:
        self.setting.set_mode(START)
        self.me = OAuthToken("a", "r", 0, tuple(SCOPES), "42", "streamer")  # a login from before
        self.assertFalse(await self.loader.load())
        self.assertRegex(self.loader.status, r"^Not loaded: .*press Connect once.*moderation:read")
        self.assertEqual(self.helix.calls, [])
        self.assertFalse(self.loader.due())
        self.time = 61.0
        self.assertTrue(self.loader.due())
        self.me = None
        await self.loader.load()
        self.assertEqual(self.loader.status, "Not loaded: Twitch is not connected")

    def test_the_setting_keeps_what_is_valid(self) -> None:
        self.assertEqual(self.setting.minutes, 10)
        self.setting.set_minutes("0")
        self.assertEqual(self.setting.minutes, 1)
        with self.assertRaises(ValueError):
            self.setting.set_mode("sometimes")
        with self.assertRaises(ValueError):
            self.setting.set_minutes("often")


if __name__ == "__main__":
    unittest.main()
