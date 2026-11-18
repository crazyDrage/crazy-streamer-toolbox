import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.flows.flow import Flow


class TestDeckStore(unittest.TestCase):
    def test_made_from_flows_until_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flows = [Flow("sway", "Sway")]
            store = DeckStore(Path(tmp) / "live_deck.json", lambda: flows)
            deck = store.load()
            self.assertEqual(deck.pages[0].buttons[0].action, "flow.sway")
            deck.pages[0].buttons[0].label = "Sway!"
            store.save(deck)
            flows.append(Flow("other", "Other"))  # a new flow doesn't appear on a saved deck by itself
            self.assertEqual([b.label for b in store.load().pages[0].buttons], ["Sway!"])
            self.assertEqual(store.version, 1)

    def test_undo_goes_back_one_save_at_a_time(self) -> None:
        """His 11-18 pick 5."""
        with tempfile.TemporaryDirectory() as tmp:
            store = DeckStore(Path(tmp) / "live_deck.json", lambda: [Flow("sway", "Sway")])
            self.assertFalse(store.undo())  # nothing saved yet
            deck = store.load()
            store.save(deck)  # the first save has nothing before it
            self.assertFalse(store.can_undo)
            for label in ("one", "two"):
                deck.pages[0].buttons[0].label = label
                store.save(deck)
            self.assertTrue(store.undo())
            self.assertEqual(store.load().pages[0].buttons[0].label, "one")
            self.assertEqual(store.version, 4)  # open Live pages draw it again
            self.assertTrue(store.undo())
            self.assertEqual(store.load().pages[0].buttons[0].label, "Sway")
            self.assertFalse(store.undo())

    def test_followed_lists_the_flow_outputs_buttons_follow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DeckStore(Path(tmp) / "live_deck.json", lambda: [Flow("mic", "Mic"), Flow("sway", "Sway")])
            deck = store.load()
            self.assertEqual(store.followed(), set())
            deck.pages[0].buttons[0].state = "active"
            store.save(deck)
            self.assertEqual(store.followed(), {("mic", "active")})  # read again after the save
