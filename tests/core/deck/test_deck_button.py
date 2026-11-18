import unittest

from streamer_toolbox.core.deck.deck_button import DeckButton


class TestDeckButton(unittest.TestCase):
    def test_state_on_look_and_ask_first_are_kept(self) -> None:
        button = DeckButton("Mic", "flow.mic", confirm=True, state="active", on_label="Muted", on_color="#e53935",
                            on_icon="mic_off", on_text_color="#000000")
        self.assertEqual(DeckButton.from_dict(button.to_dict()), button)

    def test_a_button_saved_before_has_none(self) -> None:
        button = DeckButton.from_dict({"label": "Old", "action": "flow.old"})
        self.assertEqual((button.confirm, button.state, button.on_label, button.on_color), (False, "", "", ""))
