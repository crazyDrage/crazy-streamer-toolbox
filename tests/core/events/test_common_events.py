import unittest

from streamer_toolbox.core.events.common_events import SAME, CommonEvents, common
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS


class TestCommonEvents(unittest.IsolatedAsyncioTestCase):
    def test_every_platforms_event_has_the_common_ones_fields(self) -> None:
        for kind, same in SAME.items():
            data = {key: "x" for key in EVENT_FIELDS[kind]}
            self.assertEqual(set(common(kind, data)), set(EVENT_FIELDS[same]), kind)

    def test_what_a_platform_doesnt_know_is_empty_and_the_platform_is_said(self) -> None:
        self.assertEqual(common("rumble.follow", {"user": "Ann", "platform": "rumble"}), {
            "user": "Ann", "user_login": "ann", "platform": "rumble", "source": "rumble.follow"})
        chat = common("youtube.chat", {"user": "Kit", "message": "!hi there", "command": "!hi", "args": "there",
                                       "role": "mod", "user_id": "UC2", "message_id": "m1", "platform": "youtube"})
        self.assertEqual((chat["command"], chat["role"], chat["emotes"], chat["color"], chat["platform"]),
                         ("!hi", "mod", [], "", "youtube"))
        member = common("youtube.member", {"user": "Kit", "level": "Lizard", "upgrade": False, "platform": "youtube"})
        self.assertEqual((member["tier"], member["gift"], member["source"]), (1, False, "youtube.member"))
        redeemed = common("streamsocket.event", {"event": "Lizard", "event_id": "ev1", "bits": 100, "user": "Kit",
                                                 "user_id": "7", "categories": [], "test": False,
                                                 "platform": "twitch"})
        self.assertEqual((redeemed["reward"], redeemed["cost"], redeemed["reward_id"], redeemed["source"]),
                         ("Lizard", 100, "ev1", "streamsocket.event"))
        twitch = common("twitch.redeem", {"user": "Kit", "user_login": "kit", "reward": "Hug", "input": "now",
                                          "cost": 50, "reward_id": "r1", "redemption_id": "x", "platform": "twitch"})
        self.assertEqual((twitch["reward"], twitch["input"], twitch["user_login"]), ("Hug", "now", "kit"))

    async def test_the_platforms_event_stays_and_the_common_one_comes_too(self) -> None:
        events = EventBus()
        seen: list[tuple[str, str]] = []

        async def listen(kind: str, data: dict) -> None:
            seen.append((kind, data.get("platform", "")))

        events.subscribe(CommonEvents(events).handle)
        events.subscribe(listen)
        events.publish("rumble.follow", {"user": "Ann", "platform": "rumble"})
        events.publish("timer", {"every": 1})
        for _ in range(3):
            await events.wait_idle()
        self.assertEqual(seen, [("rumble.follow", "rumble"), ("timer", ""), ("follow", "rumble")])


if __name__ == "__main__":
    unittest.main()
