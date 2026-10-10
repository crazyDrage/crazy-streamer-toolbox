import unittest

from streamer_toolbox.connections.twitch.eventsub_events import role, subscriptions, to_event


class TestEventSubEvents(unittest.TestCase):
    def test_every_subscription_has_a_mapping(self) -> None:
        for kind, _, _ in subscriptions("42"):
            self.assertIsNotNone(to_event(kind, {"broadcaster_user_id": "42", "reward": {}, "message": {}}), kind)

    def test_chat_role_and_shared_chat(self) -> None:
        mod = to_event("channel.chat.message", {"message": {"text": "hi"}, "badges": [
            {"set_id": "subscriber"}, {"set_id": "moderator"}]})
        self.assertEqual(mod[1]["role"], "mod")
        self.assertIsNone(to_event("channel.chat.message", {"broadcaster_user_id": "42",
                                                            "source_broadcaster_user_id": "77"}))
        own = to_event("channel.chat.message", {"broadcaster_user_id": "42", "source_broadcaster_user_id": "42",
                                                "message": {"text": "lizard"}})
        self.assertEqual(own[1]["message"], "lizard")
        self.assertEqual(role([]), "viewer")
        self.assertEqual(role([{"set_id": "broadcaster"}, {"set_id": "vip"}]), "broadcaster")

    def test_emotes_in_a_chat_message_and_where_they_sit(self) -> None:
        chat = to_event("channel.chat.message", {"message": {"text": " hi Kappa <3 Kappa", "fragments": [
            {"type": "text", "text": " hi "},
            {"type": "emote", "text": "Kappa", "emote": {"id": "25", "emote_set_id": "0"}},
            {"type": "text", "text": " "},
            {"type": "emote", "text": "<3", "emote": {"id": "9"}},
            {"type": "text", "text": " "},
            {"type": "emote", "text": "Kappa", "emote": {"id": "25"}}]}})[1]
        self.assertEqual(chat["message"], "hi Kappa <3 Kappa")  # trimmed: the places count from its first letter
        self.assertEqual(chat["emotes"], [{"name": "Kappa", "id": "25", "start": 3, "end": 7},
                                          {"name": "<3", "id": "9", "start": 9, "end": 10},
                                          {"name": "Kappa", "id": "25", "start": 12, "end": 16}])
        self.assertEqual(to_event("channel.chat.message", {"message": {"text": "plain"}})[1]["emotes"], [])

    def test_deleted_messages(self) -> None:
        gone = {"target_user_name": "Kit", "target_user_login": "kit", "target_user_id": "7"}
        self.assertEqual(to_event("channel.chat.message_delete", {**gone, "message_id": "m1"}),
                         ("twitch.chat_deleted", {"user": "Kit", "user_login": "kit", "user_id": "7",
                                                  "message_id": "m1"}))
        self.assertEqual(to_event("channel.chat.clear_user_messages", gone)[1],
                         {"user": "Kit", "user_login": "kit", "user_id": "7", "message_id": ""})
        self.assertEqual(to_event("channel.chat.clear", {})[1]["user_id"], "")

    def test_a_follow_and_a_raid_say_who_by_id_too(self) -> None:
        self.assertEqual(to_event("channel.follow", {"user_name": "Kit", "user_login": "kit", "user_id": "7",
                                                     "followed_at": "2026-10-09T18:00:00Z"}),
                         ("twitch.follow", {"user": "Kit", "user_login": "kit", "user_id": "7",
                                            "followed_at": "2026-10-09T18:00:00Z"}))
        self.assertEqual(to_event("channel.raid", {"from_broadcaster_user_name": "Big",
                                                   "from_broadcaster_user_login": "big",
                                                   "from_broadcaster_user_id": "9", "viewers": 40}),
                         ("twitch.raid", {"user": "Big", "user_login": "big", "user_id": "9", "viewers": 40}))

    def test_subs_gifts_cheers(self) -> None:
        self.assertEqual(to_event("channel.subscribe", {"user_name": "A", "user_login": "a", "user_id": "7",
                                                        "tier": "2000"}),
                         ("twitch.sub", {"user": "A", "user_login": "a", "user_id": "7", "tier": 2, "gift": False}))
        self.assertEqual(to_event("channel.subscription.gift", {"user_name": "A", "user_id": "7", "total": 5,
                                                                "is_anonymous": True}),
                         ("twitch.gift", {"user": "", "user_login": "", "user_id": "", "amount": 5, "tier": 1,
                                          "anonymous": True}))
        self.assertEqual(to_event("channel.cheer", {"user_name": "B", "user_login": "b", "bits": 100,
                                                    "message": "Cheer100 hi"})[1]["bits"], 100)
        self.assertEqual(to_event("channel.ad_break.begin", {"duration_seconds": 90, "is_automatic": True}),
                         ("twitch.ad_break", {"seconds": 90, "automatic": True}))


if __name__ == "__main__":
    unittest.main()
