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
        deck = Deck([DeckPage("Main", [DeckButton("Sway stop", "flow.sway", {"do": "stop"}, "#e53935", "stop",
                                                  x=3, y=1, w=2, h=2, text_color="#000000", image="lizard.png",
                                                  fill=True)], columns=6, rows=4, background="#202020")])
        self.assertEqual(Deck.from_dict(deck.to_dict()), deck)
        old = Deck.from_dict({"pages": [{"name": "Main", "buttons": [{"label": "a", "action": "a.x"}]}]})
        self.assertEqual((old.pages[0].background, old.pages[0].buttons[0].text_color,
                          old.pages[0].buttons[0].image), ("", "#ffffff", ""))

    def test_a_deck_saved_without_spots_gets_them_row_by_row(self) -> None:
        saved = {"pages": [{"name": "Main", "buttons": [{"label": n, "action": "a.x"} for n in "abcdefghijkl"]}]}
        page = Deck.from_dict(saved).pages[0]
        self.assertEqual([(b.x, b.y) for b in page.buttons[:2]], [(0, 0), (1, 0)])
        self.assertEqual((page.buttons[10].x, page.buttons[10].y), (0, 1))  # ten in a row, then the next row
        self.assertEqual((page.columns, page.rows), (10, 5))

    def test_a_new_button_takes_the_first_free_spot_and_a_full_page_gets_a_row(self) -> None:
        page = DeckPage("Main", [DeckButton("wide", "a.x", x=0, y=0, w=2, h=1), DeckButton("new", "a.x")],
                        columns=2, rows=1)
        page.place()
        self.assertEqual((page.buttons[1].x, page.buttons[1].y, page.rows), (0, 1, 2))

    def test_a_button_stays_inside_the_page(self) -> None:
        page = DeckPage("Main", [DeckButton("a", "a.x", x=0, y=0)], columns=4, rows=3)
        page.put(0, 3, 2, 2, 2)
        self.assertEqual([getattr(page.buttons[0], n) for n in "xywh"], [2, 1, 2, 2])
        page.put(0, -5, 9, 0, 9)
        self.assertEqual([getattr(page.buttons[0], n) for n in "xywh"], [0, 0, 1, 3])
        page.put(0, 3, 2, 1, 1)
        page.set_grid(2, 2)
        self.assertEqual([getattr(page.buttons[0], n) for n in "xywh"], [1, 1, 1, 1])

    def test_free_page_names(self) -> None:
        page = DeckPage("Main", [DeckButton(n, "a.x") for n in "abc"])
        deck = Deck([page, DeckPage("Page")])
        self.assertEqual(deck.free_page_name(), "Page 2")
        self.assertEqual(deck.free_page_name("Scenes"), "Scenes")
        self.assertIs(deck.page("Main"), page)
