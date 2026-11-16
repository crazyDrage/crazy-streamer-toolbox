import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_value import EventValue
from streamer_toolbox.core.upgrades.emoji_dict_upgrade import EmojiDictUpgrade


class TestEmojiDictUpgrade(unittest.TestCase):
    """Settings version 6: the chat type that came with the toolbox gets emoji_dict, once."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "event_types.json"
        events = EventTypeStore(self.path)
        chat = events.get("chat")  # as version 5 had it: no emoji_dict
        events.save("chat", replace(chat, values=tuple(v for v in chat.values if v.name != "emoji_dict")))
        self.events = EventTypeStore(self.path)
        self.upgrade = EmojiDictUpgrade(lambda: self.events.add_values("chat", (EventValue("emoji_dict"),)))

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_the_chat_type_gets_it_at_the_end_once(self) -> None:
        self.assertEqual(["the chat event got the value emoji_dict"], self.upgrade.run())
        self.assertEqual("emoji_dict", EventTypeStore(self.path).get("chat").values[-1].name)
        self.assertEqual([], self.upgrade.run())

    def test_a_chat_type_he_made_himself_stays_as_it_is(self) -> None:
        chat = self.events.get("chat")
        self.events.save("chat", replace(chat, default=False))
        self.assertEqual([], self.upgrade.run())
        self.assertNotIn("emoji_dict", [v.name for v in self.events.get("chat").values])


if __name__ == "__main__":
    unittest.main()
