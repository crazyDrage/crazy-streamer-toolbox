import unittest

from streamer_toolbox.core.events.chat_command import chat_command


class ChatCommandTest(unittest.TestCase):
    def test_a_command_with_its_words(self) -> None:
        self.assertEqual(chat_command("!So ann  now "), ("!so", "ann  now"))

    def test_a_command_alone(self) -> None:
        self.assertEqual(chat_command("!lurk"), ("!lurk", ""))

    def test_a_plain_message_has_neither(self) -> None:
        self.assertEqual(chat_command("hello there everyone"), ("", ""))
        self.assertEqual(chat_command(""), ("", ""))
