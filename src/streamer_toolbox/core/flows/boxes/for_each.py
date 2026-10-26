from collections.abc import AsyncIterator
from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.variables.boxes.variable_box import VariableBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class ForEach(VariableBox):
    name = "for_each"
    label = "For each"
    help = "Runs what's wired to 'each' once for every value in the list, one after the other, with the value in " \
           "the variable 'item'; then goes on through 'done'"
    group = "Repeat"
    ports = ("each", "done")
    flow_only = True
    variable_fields = ("item",)
    labels = {"items": "List", "item": "Each value goes in variable"}

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"item": self.names}

    async def run(self, items: Any, item: str = "item") -> AsyncIterator[str]:
        """Checks the list first (a bad list fails the box), then hands the runner one round at a time."""
        values = to_list(items)
        self.variables.set(item, None)  # also checks the variable name before the first round

        async def rounds() -> AsyncIterator[str]:
            for value in values:
                self.variables.set(item, value)
                yield "each"
            yield "done"

        return rounds()
