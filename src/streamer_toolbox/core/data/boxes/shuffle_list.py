import random
from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


class ShuffleList(Box):
    name = "shuffle"
    label = "Shuffle list"
    help = "The list in a random order"
    group = "New list"
    flow_only = True

    async def run(self, items: Any) -> list[Any]:
        values = to_list(items)
        random.shuffle(values)
        return values
