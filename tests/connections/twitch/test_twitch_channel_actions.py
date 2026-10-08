import unittest
from datetime import datetime, timezone

from streamer_toolbox.connections.twitch.twitch_channel_actions import TwitchChannelActions
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_helix import FakeHelix

NOW = datetime(2026, 10, 2, 21, 0, tzinfo=timezone.utc)
CHANNEL = {"data": [{"title": "Lizards!", "game_name": "Just Chatting", "tags": ["English", "VTuber"]}]}
LIVE = {"data": [{"viewer_count": 17, "started_at": "2026-10-02T19:30:00Z"}]}
VIEWER = {"data": [{"id": "77", "login": "viewer", "display_name": "Viewer", "profile_image_url": "https://p",
                    "description": "hi", "created_at": "2020-01-01T00:00:00Z", "broadcaster_type": "affiliate"}]}


class TestTwitchChannelActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.helix = FakeHelix({("GET", "channels"): CHANNEL, ("GET", "streams"): LIVE, ("GET", "users"): VIEWER})
        self.actions = ActionRegistry()
        me = OAuthToken("a", "r", 0, (), "42", "crazydrage")
        TwitchChannelActions(self.helix, lambda: me, now=lambda: NOW).add_to(self.actions)

    async def run_box(self, name: str, **params):
        return await self.actions.run(f"twitch.{name}", **params)

    async def test_channel_live(self) -> None:
        self.assertEqual(await self.run_box("get_channel"), {
            "live": True, "viewers": 17, "uptime_seconds": 5400, "title": "Lizards!", "category": "Just Chatting",
            "tags": ["English", "VTuber"]})
        self.assertEqual(self.helix.sent("GET", "streams"), [({"user_id": "42"}, {})])

    async def test_channel_offline(self) -> None:
        self.helix.answers[("GET", "streams")] = {"data": []}
        info = await self.run_box("get_channel")
        self.assertEqual((info["live"], info["viewers"], info["uptime_seconds"]), (False, 0, 0))

    async def test_title(self) -> None:
        await self.run_box("set_title", title="  New title ")
        self.assertEqual(self.helix.sent("PATCH", "channels"), [({"broadcaster_id": "42"}, {"title": "New title"})])
        with self.assertRaisesRegex(ValueError, "up to 140"):
            await self.run_box("set_title", title="x" * 141)

    async def test_category_exact_then_search(self) -> None:
        self.helix.answers[("GET", "games")] = {"data": []}
        self.helix.answers[("GET", "search/categories")] = {"data": [{"id": "509658", "name": "Just Chatting"}]}
        self.assertEqual(await self.run_box("set_category", category="just chat"), "Just Chatting")
        self.assertEqual(self.helix.sent("PATCH", "channels"), [({"broadcaster_id": "42"}, {"game_id": "509658"})])
        self.helix.answers[("GET", "search/categories")] = {"data": []}
        with self.assertRaisesRegex(KeyError, "no category like 'zzz'"):
            await self.run_box("set_category", category="zzz")

    async def test_ad_schedule(self) -> None:
        self.helix.answers[("GET", "channels/ads")] = {"data": [{"next_ad_at": "2026-10-02T21:05:00+00:00",
                                                                 "duration": 60, "snooze_count": 2}]}
        self.assertEqual(await self.run_box("get_ad_schedule"),
                         {"next_in_seconds": 300, "length_seconds": 60, "snoozes": 2})
        self.helix.answers[("GET", "channels/ads")] = {"data": [{"next_ad_at": 0}]}  # none planned
        self.assertEqual((await self.run_box("get_ad_schedule"))["next_in_seconds"], 0)

    async def test_user(self) -> None:
        user = await self.run_box("get_user", user="@Viewer")
        self.assertEqual((user["id"], user["name"], user["type"]), ("77", "Viewer", "affiliate"))
        self.assertEqual(self.helix.sent("GET", "users"), [({"login": "viewer"}, {})])
        self.helix.answers[("GET", "users")] = {"data": []}
        with self.assertRaisesRegex(KeyError, "no user 'ghost'"):
            await self.run_box("get_user", user="ghost")

    async def test_followers(self) -> None:
        self.helix.answers[("GET", "channels/followers")] = lambda params: (
            {"total": 120, "data": [{"followed_at": "2025-05-05T00:00:00Z"}]} if "user_id" in params
            else {"total": 120, "data": []})
        self.assertEqual(await self.run_box("get_followers"), {"count": 120, "follows": False, "since": ""})
        self.assertEqual(await self.run_box("get_followers", user="viewer"),
                         {"count": 120, "follows": True, "since": "2025-05-05T00:00:00Z"})


if __name__ == "__main__":
    unittest.main()
