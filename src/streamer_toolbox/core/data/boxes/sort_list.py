from typing import Any

from streamer_toolbox.core.data.box_value import to_bool, to_list
from streamer_toolbox.core.interfaces.box import Box


class SortList(Box):
    name = "sort"
    label = "Sort list"
    help = "The list sorted (numbers by value, text A-Z); by = a field to sort objects by, e.g. value for Top " \
           "viewers"
    group = "New list"
    flow_only = True

    async def run(self, items: Any, descending: bool = False, by: str = "") -> list[Any]:
        def key(item: Any) -> tuple:
            value = item.get(by, "") if by and isinstance(item, dict) else item
            try:
                return 0, float(value), ""
            except (TypeError, ValueError):
                return 1, 0.0, str(value).casefold()

        return sorted(to_list(items), key=key, reverse=to_bool(descending))
