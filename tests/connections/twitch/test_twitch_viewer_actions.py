import unittest

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.twitch.twitch_auth import EXTRA_SCOPES
from streamer_toolbox.connections.twitch.twitch_viewer_actions import TwitchViewerActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_helix import FakeHelix

KIT = {"data": [{"id": "77", "login": "kit", "display_name": "Kit"}]}
ONE = {"data": [{"user_id": "77"}]}
NONE = {"data": []}


class TestTwitchViewerActions(unittest.IsolatedAsyncioTestCase):
    def _box(self, **answers):
        self.helix = FakeHelix({("GET", "users"): KIT, ("GET", "moderation/moderators"): NONE,
                                ("GET", "channels/vips"): NONE, ("GET", "subscriptions"): NONE,
                                **{("GET", path): answer for path, answer in answers.items()}})
        self.me = OAuthToken("a", "r", 0, tuple(EXTRA_SCOPES), "42", "streamer")
        actions = ActionRegistry()
        TwitchViewerActions(self.helix, lambda: self.me).add_to(actions)
        return lambda **params: actions.run("twitch.viewer_role", **params)

    async def test_the_highest_role_and_each_one_as_yes_or_no(self) -> None:
        role = self._box()
        self.assertEqual(await role(user_id="77"),
                         {"role": "viewer", "is_mod": False, "is_vip": False, "is_sub": False, "tier": 0})
        self.assertEqual(self.helix.sent("GET", "users"), [])  # an id needs no look-up by name
        for path in ("moderation/moderators", "channels/vips", "subscriptions"):
            self.assertEqual(self.helix.sent("GET", path), [({"broadcaster_id": "42", "user_id": "77"}, {})])
        role = self._box(**{"subscriptions": {"data": [{"user_id": "77", "tier": "2000"}]}})
        self.assertEqual(await role(user_id="77"),
                         {"role": "sub", "is_mod": False, "is_vip": False, "is_sub": True, "tier": 2})
        role = self._box(**{"channels/vips": ONE, "subscriptions": {"data": [{"user_id": "77", "tier": "1000"}]}})
        self.assertEqual((await role(user_id="77"))["role"], "vip")
        role = self._box(**{"moderation/moderators": ONE, "subscriptions": {"data": [{"tier": "1000"}]}})
        self.assertEqual(await role(user_id="77"),
                         {"role": "mod", "is_mod": True, "is_vip": False, "is_sub": True, "tier": 1})

    async def test_by_name_and_the_streamer_needs_no_question(self) -> None:
        role = self._box(**{"moderation/moderators": ONE})
        self.assertEqual((await role(user="@Kit"))["role"], "mod")
        self.assertEqual(self.helix.sent("GET", "users"), [({"login": "kit"}, {})])
        role = self._box()
        self.assertEqual((await role(user_id="42"))["role"], "broadcaster")
        self.assertEqual(self.helix.calls, [])

    async def test_what_is_wrong_is_said(self) -> None:
        role = self._box()
        with self.assertRaisesRegex(ValueError, "Which viewer"):
            await role()
        role = self._box(users=NONE)
        with self.assertRaisesRegex(LookupError, "^Twitch has no user 'ghost'"):
            await role(user="ghost")
        role = self._box()
        self.me = OAuthToken("a", "r", 0, ("user:read:chat", "moderation:read"), "42", "streamer")
        with self.assertRaisesRegex(PermissionError, r"press Connect once.*needs channel:read:vips\)"):
            await role(user_id="77")
        self.assertEqual(self.helix.calls, [])


if __name__ == "__main__":
    unittest.main()
