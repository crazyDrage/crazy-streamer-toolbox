from typing import Any

from streamer_toolbox.core.data.box_value import same, to_list
from streamer_toolbox.core.interfaces.box import Box


class FindInList(Box):
    name = "find"
    label = "Find in list"
    help = "Where the value is in the list (1 = first), 0 if it isn't there"
    group = "Read"
    flow_only = True

    async def run(self, items: Any, value: Any) -> int:
        return next((i for i, item in enumerate(to_list(items), 1) if same(item, value)), 0)
