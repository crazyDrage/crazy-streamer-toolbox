from dataclasses import dataclass
from typing import Any

# the kinds of pieces an alert's words are made of: kind → (its name, what it says by default)
PARTS: dict[str, tuple[str, str]] = {
    "text": ("Text line", ""),  # its words are the alert's Text ("{user} just followed!")
    "name": ("Name", "{user}"),
    "amount": ("Amount", "{amount}"),
    "message": ("Their message", "{message}"),
}
ALIGNS = {"left": "Left", "center": "Middle", "right": "Right"}


@dataclass(frozen=True)
class AlertPart:
    """One piece of an alert's words, placed on its own: a text line, the viewer's name, the amount, their
    message. An alert has a list of them (AlertRule.parts; a kind can be in it more than once). A piece is in
    the stack below (or above) the picture, or **on the picture** at x / y (percent of the picture: where the
    left end, middle or right end of its top edge is, by `align`), so a picture that is a card with boxes to
    fill ("Name:", "Age: __ months", "Message:") gets each piece in its box. width = how much of the picture's
    width it may use before it wraps (0 = as wide as it needs), size = pixels (0 = the alert's text size),
    color = "" for the alert's own. `text` is what it says, with {user}, {amount}, ... ("" = its default)."""

    kind: str
    text: str = ""
    on_picture: bool = False
    x: float = 50.0
    y: float = 50.0
    width: float = 0.0
    size: float = 0.0
    color: str = ""
    align: str = "center"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlertPart":
        return cls(str(data["kind"]), str(data.get("text", "")),
                   bool(data.get("on_picture", False)), _between(data.get("x", 50), 0, 100),
                   _between(data.get("y", 50), 0, 100), _between(data.get("width", 0), 0, 100),
                   _between(data.get("size", 0), 0, 300), str(data.get("color", "")).strip(),
                   data.get("align") if data.get("align") in ALIGNS else "center")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "text": self.text, "on_picture": self.on_picture,
                "x": self.x, "y": self.y, "width": self.width, "size": self.size, "color": self.color,
                "align": self.align}

    @property
    def title(self) -> str:
        return PARTS[self.kind][0]

    @property
    def template(self) -> str:
        """What it says before the values are filled in (a text line without words of its own says the alert's
        Text)."""
        return self.text or PARTS[self.kind][1]

    def view(self, index: int, text: str) -> dict[str, Any]:
        """What the overlay gets for this piece, with its words filled in. index = its place in the alert's
        list (the editor's frame names a dragged piece by it)."""
        return {"kind": self.kind, "index": index, "text": text, "on_picture": self.on_picture, "x": self.x,
                "y": self.y, "width": self.width, "size": self.size, "color": self.color, "align": self.align}


def _between(value: Any, lowest: float, highest: float) -> float:
    try:
        return max(lowest, min(float(value), highest))
    except (TypeError, ValueError):
        return lowest
