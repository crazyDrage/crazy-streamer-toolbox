from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


class GetFromList(Box):
    name = "get"
    label = "Get from list"
    help = "The value at a position: 1 = first, -1 = last"
    group = "Read"
    flow_only = True
    data_only = True  # no run wire: it runs whenever a box needs its value (his OPEN 92)
    typed = ("default",)

    async def run(self, items: Any, position: int = 1, default: Any = "") -> Any:
        """default: given back when there's no such position (empty = the box fails)."""
        values, position = to_list(items), int(position)
        if position == 0 or abs(position) > len(values):
            if default not in ("", None):
                return default
            raise IndexError(f"no position {position} in a list of {len(values)}")
        return values[position - 1 if position > 0 else position]
