from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


class InsertIntoList(Box):
    name = "insert"
    label = "Insert into list"
    help = "The list with a value put in at a position (1 = first, empty = at the end)"
    group = "New list"
    flow_only = True
    typed = ("value",)

    async def run(self, items: Any, value: Any, position: int | None = None) -> list[Any]:
        values = to_list(items)
        if position in (None, ""):
            return values + [value]
        position = int(position)
        values.insert(position - 1 if position > 0 else len(values) + position + 1, value)
        return values
