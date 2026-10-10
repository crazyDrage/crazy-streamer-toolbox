import importlib.util
import unittest
from pathlib import Path

FILE = Path(__file__).parents[2] / "plugins" / "sammi_decks" / "lib" / "deck_filter.py"
_spec = importlib.util.spec_from_file_location("sammi_decks_deck_filter", FILE)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
DeckFilter = _module.DeckFilter

DECKS = [{"name": "sounds", "id": "1", "enabled": True,
          "buttons": [{"id": "ID38", "text": "<-"}, {"id": "lizard_sound", "text": "lizard_sound"},
                      {"id": "fart_sound", "text": "fart\nsound"}, {"id": "ID32", "text": ""}]},
         {"name": "backup", "id": "2", "enabled": False, "buttons": [{"id": "ID63", "text": "lizard backup"}]}]


class TestSammiDecksFilter(unittest.TestCase):
    """The sammi_decks plugin's DeckFilter (plugins/sammi_decks/lib/deck_filter.py)."""

    def test_hidden_decks_and_nav_buttons_are_left_out(self) -> None:
        filters = DeckFilter(["<-", "->", ""], ["backup"])
        self.assertEqual([d["name"] for d in filters.decks(DECKS)], ["sounds"])
        self.assertEqual([b["id"] for b in filters.buttons(DECKS[0])], ["lizard_sound", "fart_sound"])

    def test_search_every_shown_deck_by_text_or_id(self) -> None:
        self.assertEqual([b["id"] for _, b in DeckFilter([], []).search(DECKS, "LIZARD")],
                         ["lizard_sound", "ID63"])
        self.assertEqual([b["id"] for _, b in DeckFilter([], ["backup"]).search(DECKS, "fart sound")],
                         ["fart_sound"])  # words may be on two lines
        self.assertEqual([b["id"] for _, b in DeckFilter([], []).search(DECKS, "id63")], ["ID63"])
