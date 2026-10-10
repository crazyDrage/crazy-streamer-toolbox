import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.core.history.event_history import EventHistory
from streamer_toolbox.core.widgets.missed_subscribers import MissedSubscribers
from streamer_toolbox.core.widgets.widget_session import WidgetSession
from tests.fakes.fake_helix import FakeHelix


def sub(user_id: str, name: str) -> dict:
    return {"user_id": user_id, "user_login": name.casefold(), "user_name": name, "tier": "1000", "is_gift": False}


class TestMissedSubscribers(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        folder = Path(self._dir.name)
        self.subs = [sub("7", "Kit"), sub("8", "Vex"), sub("42", "Dragon")]  # 42 = the streamer himself

        def listed(params: dict) -> dict:  # two to a page, like Twitch's cursor
            start = int(params.get("after") or 0)
            page = self.subs[start:start + 2]
            more = start + 2 < len(self.subs)
            return {"total": len(self.subs), "data": page, "pagination": {"cursor": str(start + 2)} if more else {}}

        self.helix = FakeHelix({("GET", "subscriptions"): listed})
        self.own = {"providerId": "42"}
        self.history = EventHistory(folder / "events.jsonl")
        self.session = WidgetSession(history=self.history)
        self.path = folder / "history" / "subscribers.json"

    def tearDown(self) -> None:
        self._dir.cleanup()

    def missed(self) -> MissedSubscribers:
        return MissedSubscribers(self.helix, lambda: self.own, self.session, self.history, self.path)

    async def test_the_first_look_only_keeps_the_list(self) -> None:
        self.assertEqual(await self.missed().check(), [])
        self.assertEqual(self.path.read_text(encoding="utf-8"), '["kit", "vex"]')  # every page, not the streamer
        self.assertEqual(self.history.summary("subscriber")["total"]["count"], 0)

    async def test_a_new_name_after_a_restart_is_a_sub_that_was_missed(self) -> None:
        await self.missed().check()
        self.session.add("subscriber-latest", {"type": "subscriber", "name": "Kit", "amount": 3})
        self.subs.append(sub("9", "Ann"))  # subscribed while the toolbox was off
        self.subs.remove(self.subs[1])     # and Vex's sub ran out
        self.assertEqual(await self.missed().check(), ["Ann"])
        self.assertEqual(self.session.data["subscriber-latest"]["name"], "Ann")
        self.assertEqual([one["name"] for one in self.session.data["subscriber-recent"]], ["Ann", "Kit"])
        self.assertEqual(self.history.summary("subscriber")["total"]["count"], 2)
        self.assertTrue(self.history.recent("subscriber")[0].get("missed") or
                        self.history.recent("subscriber")[1].get("missed"))
        self.assertEqual(await self.missed().check(), [])  # told once
        self.subs.append(sub("8", "Vex"))  # Vex comes back while it's off: found again
        self.assertEqual(await self.missed().check(), ["Vex"])

    async def test_a_sub_the_toolbox_saw_itself_isnt_found_again(self) -> None:
        watcher = self.missed()
        await watcher.check()
        await watcher.handle("twitch.sub", {"user": "Ann", "user_login": "ann", "platform": "twitch"})
        await watcher.handle("twitch.follow", {"user": "Cy", "user_login": "cy"})
        self.subs.append(sub("9", "Ann"))
        self.assertEqual(await self.missed().check(), [])

    async def test_when_twitch_cant_be_asked_nothing_changes(self) -> None:
        await self.missed().check()
        self.helix.answers[("GET", "subscriptions")] = TwitchApiError(401, "no")
        self.assertEqual(await self.missed().check(), [])
        self.own = {}
        self.assertEqual(await self.missed().check(), [])
        self.assertEqual(self.path.read_text(encoding="utf-8"), '["kit", "vex"]')


if __name__ == "__main__":
    unittest.main()
