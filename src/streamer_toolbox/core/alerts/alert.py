from dataclasses import dataclass
from typing import Any

from streamer_toolbox.core.alerts.alert_look import AlertLook

MIN_SECONDS, MAX_SECONDS = 0.5, 120.0


@dataclass(frozen=True)
class Alert:
    """One alert for the overlay: a line of text (the `highlights` in it are coloured, e.g. the viewer's name), a
    picture / gif / video and a sound (files on this PC, "" = none), how long it stays and how loud it is, and
    a smaller second line (what the viewer wrote with a cheer or resub), and its look (where the text is,
    how it comes in and goes out, sizes and colours). `parts` = its words as pieces with their own places
    (AlertPart.view); empty = just the text line and the message, stacked."""

    text: str = ""
    image: str = ""
    sound: str = ""
    seconds: float = 5.0
    volume: float = 1.0
    highlights: tuple[str, ...] = ()
    message: str = ""
    look: AlertLook = AlertLook()
    parts: tuple[dict[str, Any], ...] = ()

    @property
    def shown_seconds(self) -> float:
        """How long it stays, kept between half a second and two minutes (a typo mustn't block the line)."""
        return max(MIN_SECONDS, min(float(self.seconds), MAX_SECONDS))
