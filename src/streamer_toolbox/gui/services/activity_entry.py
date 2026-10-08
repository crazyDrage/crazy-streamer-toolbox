from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ActivityEntry:
    """One action run, for the Recent list on the Live page."""

    time: datetime
    source: str   # "GUI" or the API caller's name ("sammi", "kit")
    action: str
    ok: bool
    text: str
