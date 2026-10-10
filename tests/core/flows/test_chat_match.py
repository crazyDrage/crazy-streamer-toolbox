import unittest

from streamer_toolbox.core.flows.chat_match import mode_of, to_match
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger


def chat(message: str) -> dict:
    """What TwitchConnection publishes for a chat message."""
    command, _, args = message.partition(" ")
    return {"message": message, "command": command.casefold() if command.startswith("!") else "", "args": args}


class TestChatMatch(unittest.TestCase):
    def _fires(self, mode: str, text: str, message: str) -> bool:
        return FlowTrigger("twitch.chat", to_match(mode, text)).matches("twitch.chat", chat(message))

    def test_command_with_or_without_text_after_it(self) -> None:
        for message in ("!cat", "!CAT please", "!cat  "):
            self.assertTrue(self._fires("command", "!cat", message), message)
        for message in ("!catnip", "I like !cat", "cat"):
            self.assertFalse(self._fires("command", "!cat", message), message)
        self.assertEqual(to_match("command", "Cat"), {"command": "!cat"})  # the ! is added

    def test_has_word_anywhere(self) -> None:
        for message in ("lizard", "a lizard here", "LIZARD!", "lizard lizard", "so... lizard"):
            self.assertTrue(self._fires("contains", "lizard", message), message)
        for message in ("wizard", "lizards", "blizzard"):
            self.assertFalse(self._fires("contains", "lizard", message), message)

    def test_several_words(self) -> None:
        for message in ("bl", "that is so bl", "GAY", "gay!"):
            self.assertTrue(self._fires("contains", "gay, bl", message), message)
        for message in ("blue", "able", "gaze"):
            self.assertFalse(self._fires("contains", "gay, bl", message), message)

    def test_who_may_start_it(self) -> None:
        trigger = FlowTrigger("twitch.chat", {"command": "!so", "who": "vip"})
        for who, fires in (("viewer", False), ("sub", False), ("vip", True), ("mod", True), ("broadcaster", True)):
            self.assertEqual(trigger.matches("twitch.chat", {**chat("!so vex"), "role": who}), fires, who)
        self.assertFalse(trigger.matches("twitch.chat", chat("!so vex")))  # no role = a viewer

    def test_pattern_like_sammi(self) -> None:
        self.assertTrue(self._fires("pattern", "!qa *", "!qa how are you"))
        self.assertFalse(self._fires("pattern", "!qa *", "hi !qa"))

    def test_round_trip(self) -> None:
        for mode, text in (("command", "!cat"), ("contains", "lizard"), ("contains", "gay, bl"),
                           ("pattern", "* lizard *"), ("pattern", "*lizard*"),
                           ("pattern", "!qa *")):
            self.assertEqual(mode_of(to_match(mode, text)), (mode, text))
        self.assertEqual(mode_of({"message": "!command *"}), ("pattern", "!command *"))


if __name__ == "__main__":
    unittest.main()
