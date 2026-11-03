from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


class ListSize(Box):
    name = "size"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "List size"
    help = "How many values the list has"
    group = "Read"
    flow_only = True

    async def run(self, items: Any) -> int:
        return len(to_list(items))
