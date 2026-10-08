from dataclasses import dataclass, field
from typing import Any

COLORS = ("#6d5dfc", "#1e88e5", "#00897b", "#43a047", "#f9a825", "#ef6c00", "#e53935", "#d81b60", "#8e24aa",
          "#546e7a")  # the colour picker's choices; a button may have any #rrggbb


@dataclass
class DeckButton:
    """One button of the Live deck: what it shows (label, #rrggbb colour, Material icon name) and what a press
    runs: an action (a flow is flow.<name>) with fixed values for its fields (a flow's inputs, e.g. do = stop)."""

    label: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    color: str = COLORS[0]
    icon: str = "play_arrow"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeckButton":
        return cls(str(data.get("label", "")), str(data.get("action", "")), dict(data.get("params") or {}),
                   str(data.get("color") or COLORS[0]), str(data.get("icon") or "play_arrow"))

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "action": self.action, "params": self.params, "color": self.color,
                "icon": self.icon}
