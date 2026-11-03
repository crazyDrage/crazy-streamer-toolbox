import re
from dataclasses import dataclass
from typing import Any

# what an input can hold → its name in the alert's Settings
KINDS = {"text": "Text", "number": "Number", "picture": "Picture, gif or video", "sound": "Sound"}
NAME = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class AlertInput:
    """A value an alert gets each time it plays (his round 65): the viewer's name, an amount, their message, a
    picture or a sound. Its alert's box in a flow has a field for it; the alert's words use it as {name}. The
    example is what the Test button and the preview use. amount: the one number "only from" and the bigger
    alerts go by. A picture / sound input that gets a file shows that file (when the alert has none of its own
    or says {name} there): one alert can be a whole soundboard."""

    name: str
    kind: str = "text"
    example: str = ""
    amount: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlertInput":
        kind = data.get("kind")
        return cls(clean_name(str(data.get("name", ""))) or "value", kind if kind in KINDS else "text",
                   str(data.get("example", "")), bool(data.get("amount", False)))

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "example": self.example, "amount": self.amount}

    def value(self, given: Any) -> Any:
        """What it holds for this play: a number input gives a number when it can, the rest text."""
        if self.kind == "number":
            try:
                number = float(given)
                return int(number) if number.is_integer() else number
            except (TypeError, ValueError):
                return given if given not in (None, "") else 0
        return "" if given is None else given


def clean_name(text: str) -> str:
    """An input's name as {name} can use it: lower case, letters, digits and _ ("Their Message" → their_message)."""
    name = re.sub(r"[^a-z0-9_]+", "_", text.strip().casefold()).strip("_")
    return name if NAME.fullmatch(name) else ""
