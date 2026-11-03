import unittest

from streamer_toolbox.plugins.plugin_types import plugin_types, type_label, type_order


class TestPluginTypes(unittest.TestCase):
    """His asks of 2026-11-02: plugin types to sort by, and new ones from the form's "Other" field."""

    def test_no_types_is_other_and_a_new_type_stays_itself(self) -> None:
        self.assertEqual(plugin_types(("bot", "game", "bot")), ("bot", "game"))
        self.assertEqual(plugin_types(("bot", "chat_games")), ("bot", "chat_games"))
        self.assertEqual(plugin_types(()), ("other",))

    def test_a_new_type_is_named_after_its_id(self) -> None:
        self.assertEqual((type_label("bot"), type_label("chat_games")), ("Bots", "Chat games"))

    def test_known_types_first_then_new_ones_and_other_last(self) -> None:
        self.assertEqual(type_order({"other", "zoo", "game", "bot", "art"}), ["bot", "game", "art", "zoo", "other"])
