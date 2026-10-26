import json
import unittest

from streamer_toolbox.connections.fansly.fansly_news import FanslyNews


def chat(content: str, metadata: dict, attachments: list | None = None) -> dict:
    return {"type": 10, "chatRoomMessage": {
        "chatRoomId": "100000000000000001", "senderId": "200000000000000002", "content": content, "type": 0,
        "attachments": attachments or [], "metadata": json.dumps(metadata), "id": "300000000000000003",
        "createdAt": 1751552950379, "usernameColor": "#0066ff", "username": "FoxFan", "displayname": "Fox Fan"}}


def told(*events: dict) -> dict:
    """A socket message as Fansly sends it: the event as text inside `d`, which is text too."""
    inner = [{"serviceId": 46, "event": json.dumps(event)} for event in events]
    if len(inner) == 1:
        return {"t": 10000, "d": json.dumps(inner[0])}
    return {"t": 10001, "d": json.dumps(inner)}


class TestFanslyNews(unittest.TestCase):
    def test_a_chat_message_with_who_wrote_it(self) -> None:
        events = FanslyNews().news(told(chat("!Hug everyone", {"senderIsCreator": False, "senderIsFollowing": True,
                                                                "senderSubscription": {"tierName": "Plus"}})))
        self.assertEqual(events, [("fansly.chat", {
            "user": "Fox Fan", "user_login": "foxfan", "user_id": "200000000000000002", "message": "!Hug everyone",
            "command": "!hug", "args": "everyone", "message_id": "300000000000000003", "color": "#0066ff",
            "role": "sub", "tier_name": "Plus", "following": True, "platform": "fansly"})])

    def test_the_creator_is_the_broadcaster_and_someone_without_a_tier_a_viewer(self) -> None:
        news = FanslyNews()
        self.assertEqual(news.news(told(chat("hi", {"senderIsCreator": True})))[0][1]["role"], "broadcaster")
        self.assertEqual(news.news(told(chat("hi", {"senderIsCreator": False})))[0][1]["role"], "viewer")

    def test_a_tip_is_a_fansly_tip_a_tip_and_still_a_chat_message(self) -> None:
        tip = [{"contentType": 7, "contentId": "4", "metadata": json.dumps({"amount": 5000})}]
        events = FanslyNews().news(told(chat("for you", {}, tip)))
        self.assertEqual([kind for kind, _ in events], ["fansly.tip", "tip", "fansly.chat"])
        self.assertEqual(events[0][1]["amount"], 5)
        self.assertEqual(events[1][1], {"user": "Fox Fan", "amount": 5, "currency": "USD", "message": "for you",
                                        "platform": "fansly"})

    def test_a_new_sub(self) -> None:
        events = FanslyNews().news(told({"type": 53, "subAlert": {
            "subscriberId": "200000000000000002", "subscriptionTierName": "Plus", "subscriptionStreak": 1,
            "subscriptionTotalDays": 30, "username": "FoxFan", "displayname": "Fox Fan"}}))
        self.assertEqual(events, [("fansly.sub", {
            "user": "Fox Fan", "user_login": "foxfan", "user_id": "200000000000000002", "tier_name": "Plus",
            "streak": 1, "total_days": 30, "role": "sub", "platform": "fansly"})])

    def test_several_at_once_and_nothing_from_what_it_doesnt_know(self) -> None:
        news = FanslyNews()
        self.assertEqual(len(news.news(told(chat("a", {}), {"type": 99}, chat("b", {})))), 2)
        for unknown in ({"t": 1, "d": "{}"}, {"t": 10000, "d": "not json"}, {"t": 10000}, {}):
            self.assertEqual(news.news(unknown), [])


if __name__ == "__main__":
    unittest.main()
