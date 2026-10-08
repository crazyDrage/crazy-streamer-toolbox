import unittest

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.core.widgets.latest_followers import LatestFollowers
from streamer_toolbox.core.widgets.widget_session import WidgetSession
from tests.fakes.fake_helix import FakeHelix

FOLLOWERS = {"total": 812, "data": [
    {"user_id": "7", "user_login": "kit", "user_name": "Kit", "followed_at": "2026-10-03T20:00:00Z"},
    {"user_id": "8", "user_login": "vex", "user_name": "Vex", "followed_at": "2026-10-01T10:00:00Z"}]}


class TestLatestFollowers(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.helix = FakeHelix({("GET", "channels/followers"): FOLLOWERS})
        self.now = 0.0
        self.own = {"providerId": "42"}
        self.followers = LatestFollowers(self.helix, lambda: self.own, lambda: self.now)
        self.session = WidgetSession()

    async def test_the_session_has_twitchs_latest_followers(self) -> None:
        self.assertTrue(await self.followers.fill(self.session))
        data = self.session.data
        self.assertEqual((data["follower-latest"]["name"], [f["name"] for f in data["follower-recent"]],
                          data["follower-total"]["count"], data["follower-session"]["count"]),
                         ("Kit", ["Kit", "Vex"], 812, 0))
        self.assertEqual(self.helix.sent("GET", "channels/followers"), [({"broadcaster_id": "42", "first": 25}, {})])

    async def test_twitch_is_asked_at_most_once_a_minute(self) -> None:
        await self.followers.fill(self.session)
        self.now = 30
        self.assertFalse(await self.followers.fill(self.session))
        self.now = 61
        self.assertTrue(await self.followers.fill(self.session))
        self.assertEqual(len(self.helix.calls), 2)

    async def test_when_twitch_cant_be_asked_the_session_stays(self) -> None:
        self.session.add("follower-latest", {"type": "follower", "name": "Seen"})
        self.helix.answers[("GET", "channels/followers")] = TwitchApiError(401, "no")
        self.assertFalse(await self.followers.fill(self.session))
        self.own = {}  # not logged in: Twitch isn't asked at all
        self.assertFalse(await self.followers.fill(self.session))
        self.assertEqual((self.session.data["follower-latest"]["name"], len(self.helix.calls)), ("Seen", 1))

    async def test_a_channel_without_followers_keeps_what_was_seen(self) -> None:
        self.session.add("follower-latest", {"type": "follower", "name": "Seen"})
        self.helix.answers[("GET", "channels/followers")] = {"total": 0, "data": []}
        self.assertTrue(await self.followers.fill(self.session))
        self.assertEqual(self.session.data["follower-latest"]["name"], "Seen")


if __name__ == "__main__":
    unittest.main()
