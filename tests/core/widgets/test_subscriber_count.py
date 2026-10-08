import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.core.widgets.subscriber_count import SubscriberCount
from streamer_toolbox.core.widgets.widget_session import WidgetSession
from tests.fakes.fake_helix import FakeHelix

# the shape of Twitch's real answer (2026-10-04)
SUBSCRIPTIONS = {"total": 6, "points": 8, "pagination": {}, "data": [
    {"user_id": "7", "user_login": "kit", "user_name": "Kit", "tier": "1000", "is_gift": False}]}


class TestSubscriberCount(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.helix = FakeHelix({("GET", "subscriptions"): SUBSCRIPTIONS})
        self.now = 0.0
        self.own = {"providerId": "42"}
        self.count = SubscriberCount(self.helix, lambda: self.own, lambda: self.now)

    async def test_the_session_has_twitchs_count_and_points_and_keeps_its_latest(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            session = WidgetSession(Path(folder) / "session.json")
            session.add("subscriber-latest", {"type": "subscriber", "name": "Seen", "amount": 1})
            self.assertTrue(await self.count.fill(session))
            data = session.data
            self.assertEqual((data["subscriber-total"], data["subscriber-points"], data["subscriber-latest"]["name"]),
                             ({"count": 6, "amount": 0}, {"amount": 8}, "Seen"))  # who was last isn't Twitch's to say
            self.assertEqual(self.helix.sent("GET", "subscriptions"), [({"broadcaster_id": "42", "first": 1}, {})])
            self.assertEqual(WidgetSession(Path(folder) / "session.json").data["subscriber-points"], {"amount": 8})

    async def test_asked_at_most_once_a_minute_and_not_at_all_without_a_login(self) -> None:
        session = WidgetSession()
        await self.count.fill(session)
        self.now = 30
        self.assertFalse(await self.count.fill(session))
        self.now = 61
        self.assertTrue(await self.count.fill(session))
        self.own = {}
        self.now = 200
        self.assertFalse(await self.count.fill(session))
        self.assertEqual(len(self.helix.calls), 2)

    async def test_when_twitch_refuses_the_session_stays(self) -> None:
        session = WidgetSession()
        self.helix.answers[("GET", "subscriptions")] = TwitchApiError(401, "no")
        self.assertFalse(await self.count.fill(session))
        self.assertEqual((session.data["subscriber-total"]["count"], session.data["subscriber-points"]),
                         (0, {"amount": 0}))


if __name__ == "__main__":
    unittest.main()
