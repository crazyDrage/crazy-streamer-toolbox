import unittest

from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.widgets.widget_events import TEST_EVENTS, se_event, test_event
from streamer_toolbox.core.widgets.widget_hub import WidgetHub


class TestWidgetHub(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.hub = WidgetHub()

    def test_an_event_that_didnt_reach_obs_is_kept(self) -> None:
        self.hub.not_arrived("goal", {"type": "session", "session": {}})
        self.hub.not_arrived("goal", {"type": "event", "listener": "follower-latest", "event": {}})
        self.assertEqual([(widget, listener) for _, widget, listener, _ in self.hub.missed],
                         [("goal", "follower-latest")])

    def test_a_widget_page_that_comes_back_gets_its_own_missed_events(self) -> None:
        self.hub.listen("goal")
        self.hub.test("goal", "follower-latest")
        self.hub.test("chat_box", "follower-latest")  # another widget's
        self.hub.reload("goal")
        back = self.hub.greeting("goal", self.hub.sent.run, 0)
        self.assertEqual([m["type"] for m in back], ["hello", "event", "reload"])
        self.assertEqual(self.hub.greeting("goal", self.hub.sent.run, back[-1]["id"])[1:], [])

    def test_toolbox_events_in_streamelements_words(self) -> None:
        self.assertEqual(se_event("twitch.follow", {"user": "Dragon"}),
                         ("follower-latest", {"type": "follower", "name": "Dragon"}))
        listener, resub = se_event("twitch.resub", {"user": "Kit", "tier": 2, "months": 7, "message": "hi"})
        self.assertEqual((listener, resub["amount"], resub["tier"], resub["message"], resub["gifted"]),
                         ("subscriber-latest", 7, "2000", "hi", False))
        _, gift = se_event("twitch.gift", {"user": "", "amount": 5, "tier": 1, "anonymous": True})
        self.assertEqual((gift["name"], gift["sender"], gift["amount"], gift["bulkGifted"]),
                         ("Anonymous", "Anonymous", 5, True))
        self.assertEqual(se_event("twitch.cheer", {"user": "Kit", "bits": 100, "message": "yo"})[1]["amount"], 100)
        self.assertEqual(se_event("twitch.raid", {"user": "Big", "viewers": 40}),
                         ("raid-latest", {"type": "raid", "name": "Big", "amount": 40}))
        self.assertEqual(se_event("tip", {"user": "Kit", "amount": 4.99, "currency": "EUR", "message": "snacks"}),
                         ("tip-latest", {"type": "tip", "name": "Kit", "amount": 4.99, "message": "snacks",
                                         "userCurrency": "EUR"}))
        self.assertIsNone(se_event("vts.model_loaded", {"model": "dragon"}))

    def test_other_platforms_reach_widgets_through_the_common_events(self) -> None:
        self.assertEqual(se_event("follow", {"user": "Ann", "platform": "rumble"}),
                         ("follower-latest", {"type": "follower", "name": "Ann"}))
        listener, event = se_event("chat", {"user": "Kit", "message": "hi", "platform": "youtube"})
        self.assertEqual((listener, event["service"], event["data"]["text"]), ("message", "youtube", "hi"))
        self.assertIsNone(se_event("follow", {"user": "Dragon", "platform": "twitch"}))  # twitch.follow covers it
        self.assertIsNone(se_event("redeem", {"user": "Kit", "platform": "twitch"}))

    def test_emotes_and_deleted_messages_in_streamelements_words(self) -> None:
        listener, event = se_event("twitch.chat", {"user": "Kit", "message": "hi Kappa <b>", "emotes": [
            {"name": "Kappa", "id": "25", "start": 3, "end": 7}]})
        self.assertEqual(event["data"]["tags"]["emotes"], "25:3-7")
        self.assertEqual(event["data"]["emotes"], [{
            "type": "twitch", "name": "Kappa", "id": "25", "gif": False, "start": 3, "end": 7, "urls": {
                "1": "https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/1.0",
                "2": "https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/2.0",
                "4": "https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/3.0"}}])
        self.assertTrue(event["renderedText"].startswith('hi <img src="https://static-cdn.jtvnw.net/emoticons/v2/25/'))
        self.assertTrue(event["renderedText"].endswith('class="emote"> &lt;b&gt;'))  # his words stay escaped
        self.assertEqual(se_event("twitch.chat_deleted", {"user_id": "7", "message_id": "m1"}),
                         ("delete-message", {"msgId": "m1"}))
        self.assertEqual(se_event("twitch.chat_deleted", {"user_id": "7", "message_id": ""}),
                         ("delete-messages", {"userId": "7"}))

    def test_a_chat_message_has_what_chat_widgets_read(self) -> None:
        listener, event = se_event("twitch.chat", {"user": "Dragon", "user_login": "dragon", "role": "mod",
                                                   "message": "<b>hi</b>", "message_id": "m1"})
        data = event["data"]
        self.assertEqual((listener, data["displayName"], data["nick"], data["text"], data["msgId"]),
                         ("message", "Dragon", "dragon", "<b>hi</b>", "m1"))
        self.assertEqual(event["renderedText"], "&lt;b&gt;hi&lt;/b&gt;")  # safe to put into the page as HTML
        self.assertEqual(data["badges"][0]["type"], "moderator")
        self.assertEqual((data["tags"]["mod"], data["tags"]["badges"]), ("1", "moderator/1"))
        self.assertEqual(test_event("message")["data"]["displayName"], "TestViewer")

    def test_a_typed_test_chat_text_comes_from_the_streamer(self) -> None:
        hub = WidgetHub(channel=lambda: {"username": "crazy", "providerId": "42"})
        page = hub.listen("wheel")
        hub.test("wheel", "message", " !showwheel ")
        data = page.get_nowait()["event"]["data"]
        self.assertEqual((data["text"], data["displayName"], data["userId"], data["tags"]["badges"]),
                         ("!showwheel", "crazy", "42", "broadcaster/1"))
        self.assertEqual(data["channel"], "crazy")  # written in his channel: multi channel chats check that
        hub.test("wheel", "message")
        self.assertEqual(page.get_nowait()["event"]["data"]["displayName"], "TestViewer")

    def test_every_word_comes_from_an_event_the_toolbox_really_has(self) -> None:
        for kind in ("twitch.follow", "twitch.sub", "twitch.resub", "twitch.gift", "twitch.cheer", "twitch.raid",
                     "twitch.chat", "tip"):
            self.assertIn(kind, EVENT_FIELDS)
            self.assertIn(se_event(kind, {"user": "x"})[0], TEST_EVENTS)

    async def test_an_event_counts_in_the_session_but_reaches_no_page_by_itself(self) -> None:
        """His round 74 answer 1 a: a widget gets what a flow sends it (send), nothing by itself."""
        chat, goal = self.hub.listen("chat_box"), self.hub.listen("goal")
        await self.hub.handle("twitch.cheer", {"user": "Kit", "bits": 100, "message": "yo"})
        await self.hub.handle("timer", {"every": 1})  # nothing StreamElements knows
        self.assertTrue(chat.empty() and goal.empty())
        self.assertEqual(self.hub.session.data["cheer-session"], {"count": 1, "amount": 100})
        self.assertEqual(self.hub.send("cheer-latest", {"name": "Kit", "amount": 100}, "goal"), 1)
        first, second = goal.get_nowait(), goal.get_nowait()
        self.assertEqual((first["listener"], second["session"]["cheer-session"]),
                         ("cheer-latest", {"count": 1, "amount": 100}))  # not counted twice
        self.assertTrue(chat.empty())
        await self.hub.handle("twitch.cheer", {"user": "Kit", "bits": 50, "message": ""})
        data = self.hub.session.data
        self.assertEqual((data["cheer-latest"]["amount"], data["cheer-session"]["amount"],
                          len(data["cheer-recent"]), len(self.hub.session.recents)), (50, 150, 2, 2))
        self.assertEqual(data["follower-latest"]["name"], "")  # keys a widget reads are there from the start

    async def test_chat_messages_dont_count_as_session_data(self) -> None:
        inbox = self.hub.listen("chat_box")
        await self.hub.handle("twitch.chat", {"user": "Dragon", "user_login": "dragon", "message": "hi"})
        self.hub.send("message", {"data": {"text": "hi"}}, "chat_box")
        self.assertEqual(inbox.get_nowait()["listener"], "message")
        self.assertTrue(inbox.empty())
        self.assertEqual(self.hub.session.recents, [])

    def test_test_button_and_reload_reach_only_that_widget(self) -> None:
        chat, goal, preview = self.hub.listen("chat_box"), self.hub.listen("goal"), self.hub.listen("goal", True)
        self.assertEqual((self.hub.pages("goal"), self.hub.pages("chat_box"), self.hub.pages("gone")), (1, 1, 0))
        self.assertEqual(self.hub.test("goal", "follower-latest"), 2)  # OBS and the preview
        self.assertEqual(goal.get_nowait()["event"]["name"], "TestViewer")
        self.assertEqual(self.hub.button("goal", "reset", "now"), 2)
        self.assertEqual({**goal.get_nowait(), "id": 0}, {"type": "event", "listener": "event:test", "event": {
            "listener": "widget-button", "field": "reset", "value": "now"}, "id": 0})
        self.hub.reload("goal")
        self.assertEqual(goal.get_nowait()["type"], "reload")
        self.assertTrue(chat.empty())
        self.assertEqual(self.hub.session.recents, [])  # tests leave the session alone
        self.hub.stop_listening(goal)
        self.hub.stop_listening(preview)
        self.assertEqual(self.hub.pages("goal"), 0)


if __name__ == "__main__":
    unittest.main()
