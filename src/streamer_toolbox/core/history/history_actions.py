from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.history.boxes.get_recent import GetRecent
from streamer_toolbox.core.history.boxes.get_sums import GetSums
from streamer_toolbox.core.history.event_history import EventHistory


class HistoryActions:
    """The History boxes: what the toolbox's own record (EventHistory) knows, for flows. "How many followers
    this week", "who cheered most this month", "the last five raids".

    One Box class per box, in boxes/."""

    def __init__(self, history: EventHistory) -> None:
        self._history = history

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (GetSums(self._history), GetRecent(self._history)):
            actions.add_box(box, "history")
