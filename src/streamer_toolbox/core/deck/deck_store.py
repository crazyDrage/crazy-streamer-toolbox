import json
from collections.abc import Callable
from pathlib import Path

from streamer_toolbox.core.deck.deck import Deck
from streamer_toolbox.core.files.write_whole import write_whole
from streamer_toolbox.core.flows.flow import Flow


class DeckStore:
    """The Live deck in one JSON file (config/live_deck.json), shared by every device. Until it's first saved,
    the deck is made from the flows (a button per flow)."""

    def __init__(self, path: Path, flows: Callable[[], list[Flow]]) -> None:
        self._path = path
        self._flows = flows
        self.version = 0  # goes up on every save: open Live pages draw the deck again

    def load(self) -> Deck:
        if not self._path.is_file():
            return Deck.from_flows(self._flows())
        return Deck.from_dict(json.loads(self._path.read_text(encoding="utf-8")))

    def keep(self) -> None:
        """Saves the deck as it is now when it was never saved, so flows that come in next (default flows, an
        import) don't get a button by themselves (his round 88: "Adding the default flows should not add the
        view in the live tab")."""
        if not self._path.is_file():
            self.save(self.load())

    def save(self, deck: Deck) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        write_whole(self._path, json.dumps(deck.to_dict(), indent=2, ensure_ascii=False))
        self.version += 1
