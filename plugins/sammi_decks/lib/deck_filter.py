from typing import Any

Deck = dict[str, Any]     # {"name", "id", "enabled", "buttons": [{"id", "text"}]} from the action sammi.get_decks
Button = dict[str, Any]


class DeckFilter:
    """Which decks and buttons the board shows: hidden decks left out, deck-switching buttons ("<-", "->") and
    empty ones left out, and a search over every deck (text or button ID, upper/lower case ignored)."""

    def __init__(self, hide_texts: list[str], hide_decks: list[str]) -> None:
        self._hide_texts = {t.strip().casefold() for t in hide_texts}
        self._hide_decks = set(hide_decks)

    @staticmethod
    def text(button: Button) -> str:
        """The button's text on one line ("" if it has none)."""
        return " ".join(str(button.get("text", "")).split())

    def decks(self, decks: list[Deck]) -> list[Deck]:
        return [d for d in decks if d.get("name") not in self._hide_decks]

    def buttons(self, deck: Deck) -> list[Button]:
        return [b for b in deck.get("buttons", []) if self.text(b).casefold() not in self._hide_texts]

    def search(self, decks: list[Deck], words: str) -> list[tuple[Deck, Button]]:
        """Buttons of the shown decks whose text or ID contains every word."""
        needles = words.casefold().split()
        return [(deck, button) for deck in self.decks(decks) for button in self.buttons(deck)
                if all(n in f"{self.text(button)} {button.get('id', '')}".casefold() for n in needles)]
