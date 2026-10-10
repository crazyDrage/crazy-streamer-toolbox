import unittest

from streamer_toolbox.core.deck.deck import Deck
from streamer_toolbox.core.deck.deck_button import COLORS, DeckButton
from streamer_toolbox.core.deck.deck_page import DeckPage
from streamer_toolbox.core.flows.flow import Flow


class TestDeck(unittest.TestCase):
    def test_starts_with_a_button_per_flow(self) -> None:
        deck = Deck.from_flows([Flow("sway", "Sway"), Flow("lizard_add_1", "Lizard +1")])
        self.assertEqual([p.name for p in deck.pages], ["Flows"])
        buttons = deck.pages[0].buttons
        self.assertEqual([(b.label, b.action) for b in buttons], [("Lizard +1", "flow.lizard_add_1"),
                                                                   ("Sway", "flow.sway")])
        self.assertEqual([b.color for b in buttons], list(COLORS[:2]))

    def test_round_trip_with_inputs(self) -> None:
        deck = Deck([DeckPage("Main", [DeckButton("Sway stop", "flow.sway", {"do": "stop"}, "#e53935", "stop")])])
        self.assertEqual(Deck.from_dict(deck.to_dict()), deck)

    def test_move_buttons_and_free_page_names(self) -> None:
        page = DeckPage("Main", [DeckButton(n, "a.x") for n in "abc"])
        page.move(0, 1)
        page.move(2, 5)
        self.assertEqual([b.label for b in page.buttons], ["b", "a", "c"])
        page.move(1, -1)
        self.assertEqual([b.label for b in page.buttons], ["a", "b", "c"])
        deck = Deck([page, DeckPage("Page")])
        self.assertEqual(deck.free_page_name(), "Page 2")
        self.assertEqual(deck.free_page_name("Scenes"), "Scenes")
        self.assertIs(deck.page("Main"), page)
