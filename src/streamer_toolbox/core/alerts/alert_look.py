from dataclasses import dataclass, fields
from typing import Any

TEXT_PLACES = {"below": "Below the picture", "above": "Above the picture"}
ANIMATIONS_IN = {"fade": "Fade in", "slide_down": "Slide in from above", "slide_up": "Slide in from below",
                 "zoom": "Grow", "pop": "Pop"}
ANIMATIONS_OUT = {"fade": "Fade out", "slide_up": "Slide out upwards", "slide_down": "Slide out downwards",
                  "zoom": "Shrink"}
PLACES = {"top": "Top", "center": "Middle", "bottom": "Bottom", "free": "Where I dragged it"}


@dataclass(frozen=True)
class AlertLook:
    """How an alert looks and moves. Simple: where the words are that aren't on the picture (below or above it;
    a piece on the picture has its own spot, see AlertPart), where the alert is on the screen (top, middle,
    bottom, or "free": its middle at screen_x / screen_y in percent of the screen, where he dragged it) and how
    it comes in and goes out. Advanced: how fast, the picture's height (percent of the screen), text size
    (pixels on a 1080 high canvas), colours ("" = the overlay's own, which OBS's Custom CSS can set) and the
    font."""

    text_place: str = "below"
    animation_in: str = "fade"
    animation_out: str = "fade"
    animation_seconds: float = 0.4
    place: str = "top"
    picture_height: float = 45.0
    text_size: float = 44.0
    text_color: str = ""
    accent_color: str = ""
    font: str = ""
    screen_x: float = 50.0
    screen_y: float = 50.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AlertLook":
        """What the file holds; a value that is missing or of the wrong kind keeps its default."""
        start = cls()
        values = {}
        for field in fields(cls):
            value = (data or {}).get(field.name, getattr(start, field.name))
            try:
                values[field.name] = type(getattr(start, field.name))(value)
            except (TypeError, ValueError):
                values[field.name] = getattr(start, field.name)
        return cls(**values).checked()

    def checked(self) -> "AlertLook":
        """Names that don't exist fall back, numbers stay in a range the overlay can show."""
        start = AlertLook()
        return AlertLook(
            self.text_place if self.text_place in TEXT_PLACES else start.text_place,
            self.animation_in if self.animation_in in ANIMATIONS_IN else start.animation_in,
            self.animation_out if self.animation_out in ANIMATIONS_OUT else start.animation_out,
            _between(self.animation_seconds, 0, 3), self.place if self.place in PLACES else start.place,
            _between(self.picture_height, 5, 100), _between(self.text_size, 10, 200),
            self.text_color.strip(), self.accent_color.strip(), self.font.strip(),
            _between(self.screen_x, 0, 100), _between(self.screen_y, 0, 100))

    def to_dict(self) -> dict[str, Any]:
        """Only what differs from the default: the file stays short, and so does what the overlay gets (a value
        that isn't sent is the overlay's own, e.g. from Custom CSS)."""
        start = AlertLook()
        return {f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) != getattr(start, f.name)}


def _between(value: float, lowest: float, highest: float) -> float:
    return max(lowest, min(float(value), highest))
