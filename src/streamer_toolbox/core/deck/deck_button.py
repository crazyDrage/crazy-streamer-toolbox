from dataclasses import dataclass, field
from typing import Any

COLORS = ("#6d5dfc", "#1e88e5", "#00897b", "#43a047", "#f9a825", "#ef6c00", "#e53935", "#d81b60", "#8e24aa",
          "#546e7a")  # the colour picker's choices; a button may have any #rrggbb
TEXT_COLOR = "#ffffff"
GO_TO_PAGE = "deck.page"  # a button that shows another page of the deck (params: page); not an action
PAGE_ICON = "arrow_forward"


@dataclass
class DeckButton:
    """One button of the Live deck: what it shows (label, #rrggbb colour, Material icon name) and what a press
    runs: an action (a flow is flow.<name>) with fixed values for its fields (a flow's inputs, e.g. do = stop).
    Its spot on the page is in cells of the page's grid: x, y (from the top left, 0 first) and w, h; x = -1
    means it has none yet (DeckPage.place gives it one). A picture (a file name in DeckImages) shows instead
    of the icon, whole (fill = False) or filling the button.

    State (his 11-18): `state` names an output of its flow (`active`); while that output's latest value means on
    (DeckStates), the button shows its on look: on_label / on_color / on_icon / on_text_color, each empty = the
    normal one. confirm: a press asks first (end stream, raid)."""

    label: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    color: str = COLORS[0]
    icon: str = "play_arrow"
    x: int = -1
    y: int = -1
    w: int = 1
    h: int = 1
    text_color: str = TEXT_COLOR
    image: str = ""
    fill: bool = False
    confirm: bool = False
    state: str = ""
    on_label: str = ""
    on_color: str = ""
    on_icon: str = ""
    on_text_color: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeckButton":
        return cls(str(data.get("label", "")), str(data.get("action", "")), dict(data.get("params") or {}),
                   str(data.get("color") or COLORS[0]), str(data.get("icon") or "play_arrow"),
                   int(data.get("x", -1)), int(data.get("y", -1)), int(data.get("w", 1)), int(data.get("h", 1)),
                   str(data.get("text_color") or TEXT_COLOR), str(data.get("image") or ""),
                   bool(data.get("fill", False)), bool(data.get("confirm", False)), str(data.get("state") or ""),
                   str(data.get("on_label") or ""), str(data.get("on_color") or ""), str(data.get("on_icon") or ""),
                   str(data.get("on_text_color") or ""))

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "action": self.action, "params": self.params, "color": self.color,
                "icon": self.icon, "x": self.x, "y": self.y, "w": self.w, "h": self.h,
                "text_color": self.text_color, "image": self.image, "fill": self.fill, "confirm": self.confirm,
                "state": self.state, "on_label": self.on_label, "on_color": self.on_color, "on_icon": self.on_icon,
                "on_text_color": self.on_text_color}
