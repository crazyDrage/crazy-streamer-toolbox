from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.deck.deck_button import DeckButton


@dataclass
class DeckPage:
    """One page (tab) of the Live deck: its buttons in the order they show."""

    name: str
    buttons: list[DeckButton] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeckPage":
        return cls(str(data.get("name", "Page")), [DeckButton.from_dict(b) for b in data.get("buttons", [])])

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "buttons": [b.to_dict() for b in self.buttons]}

    def move(self, index: int, by: int) -> None:
        """Moves a button by places (-1 = one to the left); stays inside the page."""
        target = max(0, min(len(self.buttons) - 1, index + by))
        self.buttons.insert(target, self.buttons.pop(index))
