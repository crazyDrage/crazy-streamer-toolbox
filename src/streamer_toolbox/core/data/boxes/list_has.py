from typing import Any

from streamer_toolbox.core.data.box_value import same, to_list
from streamer_toolbox.core.interfaces.box import Box


class ListHas(Box):
    name = "contains"
    label = "List has"
    help = "Goes on through 'then' if the list has the value, else through 'else'"
    group = "Read"
    ports = ("then", "else")
    flow_only = True

    async def run(self, items: Any, value: Any) -> bool:
        return any(same(i, value) for i in to_list(items))
