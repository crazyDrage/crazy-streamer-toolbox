from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.history.boxes.history_box import HistoryBox, KIND_CHOICES, _kind


class GetSums(HistoryBox):
    name = "summary"
    label = "Get sums"
    help = "The sums of one kind (followers, subs, cheers, raids, tips) from the toolbox's own record: session, " \
           "week, month and total, each with count and amount, and top (who gave most, the biggest one) per " \
           "session / weekly / monthly / alltime"
    group = "History"
    options = {"kind": fixed_choices(KIND_CHOICES)}
    live = True

    async def run(self, kind: str = "follower") -> dict[str, Any]:
        return self._history.summary(_kind(kind))
