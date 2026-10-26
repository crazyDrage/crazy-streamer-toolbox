from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.history.boxes.history_box import HistoryBox, KIND_CHOICES, _kind


class GetRecent(HistoryBox):
    name = "recent"
    label = "Get recent"
    help = "The newest ones of a kind from the last 40 days, newest first: each with name, amount and at (the time)"
    group = "History"
    options = {"kind": fixed_choices(KIND_CHOICES)}
    live = True

    async def run(self, kind: str = "follower", count: int = 5) -> list[dict[str, Any]]:
        return self._history.recent(_kind(kind), max(1, int(count)))
