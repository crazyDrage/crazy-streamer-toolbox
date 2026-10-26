from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


class RemoveAtPosition(Box):
    name = "remove_at"
    label = "Remove at position"
    help = "The list without the value at a position (1 = first, -1 = last)"
    group = "New list"
    flow_only = True

    async def run(self, items: Any, position: int = -1) -> list[Any]:
        values, position = to_list(items), int(position)
        if position == 0 or abs(position) > len(values):
            raise IndexError(f"no position {position} in a list of {len(values)}")
        del values[position - 1 if position > 0 else position]
        return values
