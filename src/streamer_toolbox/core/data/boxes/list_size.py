from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


class ListSize(Box):
    name = "size"
    label = "List size"
    help = "How many values the list has"
    group = "Read"
    flow_only = True

    async def run(self, items: Any) -> int:
        return len(to_list(items))
