from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.deck.deck_button import DeckButton

COLUMNS, ROWS = 10, 5  # a new page's grid
MOST = 40  # columns or rows a page may have


@dataclass
class DeckPage:
    """One page (tab) of the Live deck: a grid of columns x rows cells and its buttons, each at its own spot
    with its own size (like a SAMMI deck: he puts them where he wants). Buttons may lie on each other.
    background: a #rrggbb behind the buttons; empty = the look's own."""

    name: str
    buttons: list[DeckButton] = field(default_factory=list)
    columns: int = COLUMNS
    rows: int = ROWS
    background: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeckPage":
        page = cls(str(data.get("name", "Page")), [DeckButton.from_dict(b) for b in data.get("buttons", [])],
                   _within(data.get("columns", COLUMNS)), _within(data.get("rows", ROWS)),
                   str(data.get("background") or ""))
        page.place()
        return page

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "columns": self.columns, "rows": self.rows, "background": self.background,
                "buttons": [b.to_dict() for b in self.buttons]}

    def place(self) -> None:
        """Gives every button without a spot the first free one, row by row (a deck saved before buttons had
        spots, a new button); the page gets more rows when it is full."""
        for button in self.buttons:
            if button.x < 0 or button.y < 0:
                button.w, button.h = min(max(button.w, 1), self.columns), max(button.h, 1)
                button.x, button.y = self._free_spot(button)

    def put(self, index: int, x: int, y: int, w: int, h: int) -> None:
        """Moves a button to a spot and size; it stays inside the page."""
        button = self.buttons[index]
        button.w, button.h = min(max(w, 1), self.columns), min(max(h, 1), self.rows)
        button.x = min(max(x, 0), self.columns - button.w)
        button.y = min(max(y, 0), self.rows - button.h)

    def set_grid(self, columns: int, rows: int) -> None:
        """Changes how many cells the page has; buttons that would be outside move back in."""
        self.columns, self.rows = _within(columns), _within(rows)
        for index, button in enumerate(self.buttons):
            self.put(index, button.x, button.y, button.w, button.h)

    def _free_spot(self, button: DeckButton) -> tuple[int, int]:
        placed = [b for b in self.buttons if b is not button and b.x >= 0 and b.y >= 0]
        y = 0
        while True:
            for x in range(self.columns - button.w + 1):
                if not any(x < b.x + b.w and b.x < x + button.w and y < b.y + b.h and b.y < y + button.h
                           for b in placed):
                    self.rows = max(self.rows, y + button.h)
                    return x, y
            y += 1


def _within(number: Any) -> int:
    return min(max(int(number), 1), MOST)
