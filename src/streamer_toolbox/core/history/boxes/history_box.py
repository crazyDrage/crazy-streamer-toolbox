from streamer_toolbox.core.history.event_history import EventHistory
from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.widgets.widget_session import KINDS


KIND_CHOICES = {kind: kind.capitalize() + "s" for kind in KINDS if kind != "host"}


class HistoryBox(Box):
    """What the history boxes share (not a box itself: it has no run).

    The History boxes: what the toolbox's own record (EventHistory) knows, for flows. "How many followers
    this week", "who cheered most this month", "the last five raids"."""

    def __init__(self, history: EventHistory) -> None:
        self._history = history


def _kind(kind: str) -> str:
    kind = str(kind).strip().casefold().removesuffix("s")
    if kind not in KIND_CHOICES:
        raise ValueError(f"no history of {kind!r}: pick one of {', '.join(KIND_CHOICES)}")
    return kind
