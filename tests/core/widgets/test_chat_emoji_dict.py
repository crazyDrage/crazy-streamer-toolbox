import unittest

from streamer_toolbox.core.widgets.widget_events import dict_emotes, input_event

KAPPA = "https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/3.0"
KEPT = "/toolbox/media/flows/box/twitch_pfp_and_chat_emotes/n6/abc_kitWave.png"


class TestChatEmojiDict(unittest.TestCase):
    """His 11-16: the chat event has emoji_dict, not emotes; imported StreamElements chat widgets still get
    their emotes (data.emotes, the tags, renderedText) from it."""

    def test_the_words_of_the_dictionary_where_they_are(self) -> None:
        self.assertEqual([{"name": "Kappa", "id": "25", "start": 3, "end": 7, "url": KAPPA},
                          {"name": "kitWave", "id": "kitWave", "start": 9, "end": 15, "url": KEPT},
                          {"name": "Kappa", "id": "25", "start": 17, "end": 21, "url": KAPPA}],
                         dict_emotes("hi Kappa kitWave Kappa kappa Kappas", {"Kappa": KAPPA, "kitWave": KEPT}))
        self.assertEqual([], dict_emotes("Kappa", None))
        self.assertEqual([], dict_emotes("Kappa", "not a dictionary"))

    def test_a_streamelements_chat_message_gets_them(self) -> None:
        event = input_event("chat", {"user": "Kit", "message": "hi Kappa", "platform": "twitch",
                                     "emoji_dict": {"Kappa": KAPPA}})
        self.assertEqual("25:3-7", event["data"]["tags"]["emotes"])
        self.assertEqual([("Kappa", "25", KAPPA)],
                         [(e["name"], e["id"], e["urls"]["1"]) for e in event["data"]["emotes"]])
        self.assertIn(f'<img src="{KAPPA}"', event["renderedText"])
        self.assertTrue(event["renderedText"].startswith("hi "))


if __name__ == "__main__":
    unittest.main()
