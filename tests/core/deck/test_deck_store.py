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
