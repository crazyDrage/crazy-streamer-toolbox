import unittest
from datetime import datetime, timezone

from streamer_toolbox.connections.twitch.twitch_auth import EXTRA_SCOPES
from streamer_toolbox.connections.twitch.twitch_stream_actions import TwitchStreamActions
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from tests.fakes.fake_helix import FakeHelix

NOW = datetime(2026, 10, 3, 21, 0, tzinfo=timezone.utc)
VIEWER = {"data": [{"id": "77", "login": "kit", "display_name": "Kit"}]}
CLIPS = {"data": [
    {"id": "A", "url": "https://clips.twitch.tv/A", "title": "long", "duration": 55.0, "view_count": 90},
    {"id": "B", "url": "https://clips.twitch.tv/B", "title": "short", "duration": 12.5, "view_count": 40},
    {"id": "C", "url": "https://clips.twitch.tv/C", "title": "tiny", "duration": 5.0, "view_count": 3}]}
POLL = {"data": [{"id": "p1", "status": "ACTIVE", "choices": [{"title": "Yes", "votes": 7},
                                                             {"title": "No", "votes": 2}]}]}
PREDICTION = {"data": [{"id": "x1", "status": "ACTIVE", "outcomes": [{"id": "o1", "title": "Win"},
                                                                    {"id": "o2", "title": "Lose"}]}]}


class TestTwitchStreamActions(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.helix = FakeHelix({("GET", "users"): VIEWER, ("GET", "clips"): CLIPS, ("GET", "polls"): POLL,
                                ("GET", "predictions"): PREDICTION})
        self.me = OAuthToken("a", "r", 0, tuple(EXTRA_SCOPES), "42", "streamer")
        self.actions = ActionRegistry()
        TwitchStreamActions(self.helix, lambda: self.me, pick=lambda clips: clips[-1], now=lambda: NOW) \
            .add_to(self.actions)

    async def run_box(self, name: str, **params):
        return await self.actions.run(f"twitch.{name}", **params)

    async def test_a_login_from_before_says_press_connect(self) -> None:
        self.me = OAuthToken("a", "r", 0, ("user:read:chat",), "42", "streamer")
        for name, params in (("create_clip", {}), ("shoutout", {"user": "kit"}), ("announce", {"message": "hi"}),
                             ("start_poll", {"title": "t", "choices": "a,b"}), ("run_ad", {}), ("get_chatters", {}),
                             ("timeout", {"user": "kit"}), ("start_raid", {"user": "kit"}),
                             ("chat_mode", {"emote_only": "on"}), ("end_prediction", {})):
            with self.assertRaisesRegex(PermissionError, "press Connect once", msg=name):
                await self.run_box(name, **params)
        self.assertEqual(self.helix.calls, [])  # Twitch wasn't asked
        self.assertEqual((await self.run_box("get_clips"))["count"], 3)  # clips need no permission

    async def test_clips_of_a_channel_filtered_and_one_picked(self) -> None:
        found = await self.run_box("get_clips", user="@Kit", count=500, max_seconds=30, days=7)
        self.assertEqual((found["count"], [c["id"] for c in found["clips"]], found["url"], found["seconds"]),
                         (2, ["B", "C"], "https://clips.twitch.tv/C", 5.0))
        self.assertEqual(self.helix.sent("GET", "clips"), [({
            "broadcaster_id": "77", "first": 100, "started_at": "2026-09-26T21:00:00Z",
            "ended_at": "2026-10-03T21:00:00Z"}, {})])
        self.helix.answers[("GET", "clips")] = {"data": []}
        self.assertEqual((await self.run_box("get_clips"))["url"], "")  # none: empty, not an error

    async def test_clip_shoutout_announcement_raid_ad(self) -> None:
        self.helix.answers[("POST", "clips")] = {"data": [{"id": "Z", "edit_url": "https://edit"}]}
        self.assertEqual((await self.run_box("create_clip"))["url"], "https://clips.twitch.tv/Z")
        await self.run_box("shoutout", user="kit")
        self.assertEqual(self.helix.sent("POST", "chat/shoutouts"), [(
            {"from_broadcaster_id": "42", "to_broadcaster_id": "77", "moderator_id": "42"}, {})])
        await self.run_box("announce", message=" Hello ", color="purple")
        self.assertEqual(self.helix.sent("POST", "chat/announcements"), [(
            {"broadcaster_id": "42", "moderator_id": "42"}, {"message": "Hello", "color": "purple"})])
        await self.run_box("start_raid", user="kit")
        await self.run_box("cancel_raid")
        self.assertEqual(self.helix.sent("POST", "raids"), [({"from_broadcaster_id": "42",
                                                               "to_broadcaster_id": "77"}, {})])
        self.assertEqual(self.helix.sent("DELETE", "raids"), [({"broadcaster_id": "42"}, {})])
        self.helix.answers[("POST", "channels/commercial")] = {"data": [{"length": 60, "retry_after": 480}]}
        self.assertEqual(await self.run_box("run_ad", seconds=60), {"seconds": 60, "retry_after": 480})
        with self.assertRaisesRegex(ValueError, "30, 60, 90"):
            await self.run_box("run_ad", seconds=45)

    async def test_chat_mode_changes_only_what_is_filled_in(self) -> None:
        await self.run_box("chat_mode", emote_only="on", slow_seconds=1)
        await self.run_box("chat_mode", slow_seconds=0, followers_minutes=-1, subscribers_only="off")
        self.assertEqual([body for _, body in self.helix.sent("PATCH", "chat/settings")], [
            {"emote_mode": True, "slow_mode": True, "slow_mode_wait_time": 3},
            {"subscriber_mode": False, "slow_mode": False, "follower_mode": False}])
        with self.assertRaisesRegex(ValueError, "nothing to change"):
            await self.run_box("chat_mode")

    async def test_timeout_ban_unban_chatters(self) -> None:
        await self.run_box("timeout", user="kit", seconds=30, reason="spam")
        await self.run_box("timeout", user="kit", seconds=0)
        self.assertEqual([body for _, body in self.helix.sent("POST", "moderation/bans")], [
            {"data": {"user_id": "77", "reason": "spam", "duration": 30}},
            {"data": {"user_id": "77", "reason": ""}}])
        await self.run_box("unban", user="kit")
        self.assertEqual(self.helix.sent("DELETE", "moderation/bans"), [(
            {"broadcaster_id": "42", "moderator_id": "42", "user_id": "77"}, {})])
        self.helix.answers[("GET", "chat/chatters")] = {"total": 2, "data": [{"user_name": "Kit"},
                                                                            {"user_login": "vex"}]}
        self.assertEqual(await self.run_box("get_chatters"), {"count": 2, "names": ["Kit", "vex"]})

    async def test_poll(self) -> None:
        self.helix.answers[("POST", "polls")] = {"data": [{"id": "p1"}]}
        self.assertEqual(await self.run_box("start_poll", title="Again?", choices="Yes, No", seconds=5), "p1")
        self.assertEqual(self.helix.sent("POST", "polls")[0][1], {
            "broadcaster_id": "42", "title": "Again?", "choices": [{"title": "Yes"}, {"title": "No"}],
            "duration": 15})
        self.assertEqual(await self.run_box("end_poll"), {
            "winner": "Yes", "votes": 7, "choices": [{"title": "Yes", "votes": 7}, {"title": "No", "votes": 2}]})
        self.assertEqual(self.helix.sent("PATCH", "polls")[0][1], {"broadcaster_id": "42", "id": "p1",
                                                                   "status": "TERMINATED"})
        with self.assertRaisesRegex(ValueError, "2 to 5 are needed, there are 1"):
            await self.run_box("start_poll", title="t", choices=["only"])
        self.helix.answers[("GET", "polls")] = {"data": [{"id": "p0", "status": "COMPLETED"}]}
        with self.assertRaisesRegex(RuntimeError, "no poll is running"):
            await self.run_box("end_poll")

    async def test_prediction(self) -> None:
        self.helix.answers[("POST", "predictions")] = {"data": [{"id": "x1"}]}
        self.assertEqual(await self.run_box("start_prediction", title="Boss?", outcomes=["Win", "Lose"]), "x1")
        await self.run_box("end_prediction", how="winner", winner="lose")
        await self.run_box("end_prediction", how="cancel")
        self.assertEqual([body for _, body in self.helix.sent("PATCH", "predictions")], [
            {"broadcaster_id": "42", "id": "x1", "status": "RESOLVED", "winning_outcome_id": "o2"},
            {"broadcaster_id": "42", "id": "x1", "status": "CANCELED"}])
        with self.assertRaisesRegex(KeyError, "it has: Win, Lose"):
            await self.run_box("end_prediction", how="winner", winner="draw")


if __name__ == "__main__":
    unittest.main()
