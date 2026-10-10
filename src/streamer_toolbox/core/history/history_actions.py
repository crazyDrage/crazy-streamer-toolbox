from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.history.event_history import EventHistory
from streamer_toolbox.core.widgets.widget_session import KINDS

KIND_CHOICES = {kind: kind.capitalize() + "s" for kind in KINDS if kind != "host"}


class HistoryActions:
    """The History boxes: what the toolbox's own record (EventHistory) knows, for flows. "How many followers
    this week", "who cheered most this month", "the last five raids"."""

    def __init__(self, history: EventHistory) -> None:
        self._history = history

    def add_to(self, actions: ActionRegistry) -> None:
        async def kinds() -> dict[str, str]:
            return KIND_CHOICES

        actions.add("history.summary", self.summary, "The sums of one kind (followers, subs, cheers, raids, tips) "
                    "from the toolbox's own record: session, week, month and total, each with count and amount, "
                    "and top (who gave most, the biggest one) per session / weekly / monthly / alltime",
                    "Get sums", group="History", options={"kind": kinds}, live=True)
        actions.add("history.recent", self.recent, "The newest ones of a kind from the last 40 days, newest "
                    "first: each with name, amount and at (the time)", "Get recent", group="History",
                    options={"kind": kinds}, live=True)

    async def summary(self, kind: str = "follower") -> dict[str, Any]:
        return self._history.summary(_kind(kind))

    async def recent(self, kind: str = "follower", count: int = 5) -> list[dict[str, Any]]:
        return self._history.recent(_kind(kind), max(1, int(count)))


def _kind(kind: str) -> str:
    kind = str(kind).strip().casefold().removesuffix("s")
    if kind not in KIND_CHOICES:
        raise ValueError(f"no history of {kind!r}: pick one of {', '.join(KIND_CHOICES)}")
    return kind
