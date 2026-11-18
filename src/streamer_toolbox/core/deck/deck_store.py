import json
from collections.abc import Callable
from pathlib import Path

from streamer_toolbox.core.deck.deck import Deck
from streamer_toolbox.core.files.write_whole import write_whole
from streamer_toolbox.core.flows.flow import Flow

UNDO_STEPS = 50  # saves that can be undone (in memory, since the toolbox started)


class DeckStore:
    """The Live deck in one JSON file (config/live_deck.json), shared by every device. Until it's first saved,
    the deck is made from the flows (a button per flow)."""

    def __init__(self, path: Path, flows: Callable[[], list[Flow]]) -> None:
        self._path = path
        self._flows = flows
        self.version = 0  # goes up on every save: open Live pages draw the deck again
        self._history: list[str] = []  # the file as it was before each save, newest last (undo)
        self._followed_cache: set[tuple[str, str]] | None = None
        self._followed_at = -1

    def followed(self) -> set[tuple[str, str]]:
        """(flow name, output) of every button with a state (DeckStates keeps those through a restart). Read
        again only after a save."""
        if self._followed_at != self.version or self._followed_cache is None:
            self._followed_at = self.version
            self._followed_cache = {(b.action[5:], b.state) for page in self.load().pages for b in page.buttons
                                    if b.state and b.action.startswith("flow.")}
        return self._followed_cache

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    def undo(self) -> bool:
        """The deck as it was before the last save (any device's; his 11-18 pick 5). Kept since the toolbox
        started, the last UNDO_STEPS saves. False: nothing to undo."""
        if not self._history:
            return False
        write_whole(self._path, self._history.pop())
        self.version += 1
        return True

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
        if self._path.is_file():
            self._history = [*self._history, self._path.read_text(encoding="utf-8")][-UNDO_STEPS:]
        write_whole(self._path, json.dumps(deck.to_dict(), indent=2, ensure_ascii=False))
        self.version += 1
