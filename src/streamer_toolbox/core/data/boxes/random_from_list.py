import random
from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


class RandomFromList(Box):
    name = "random"
    label = "Random from list"
    help = "A random value from the list"
    group = "Read"
    flow_only = True

    async def run(self, items: Any) -> Any:
        values = to_list(items)
        if not values:
            raise IndexError("the list is empty")
        return random.choice(values)
