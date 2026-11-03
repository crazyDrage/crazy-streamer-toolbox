from collections.abc import AsyncIterator
from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.flows.box_signals import ALWAYS, NEXT
from streamer_toolbox.core.variables.boxes.variable_box import VariableBox
from streamer_toolbox.core.variables.variable_store import VariableStore


class ForEach(VariableBox):
    name = "for_each"
    label = "For each"
    help = "Runs what's wired to 'each' once for every value in the list, one after the other: the next round " \
           "starts when the boxes after 'each' are done, or as soon as a wire reaches its 'next' dot. The value " \
           "is on its orange dot 'item' (and in the variable 'item'), 'number' counts 1, 2, 3, ...; then goes " \
           "on through 'done'"
    group = "Repeat"
    ports = ("each", "done")
    flow_only = True
    variable_fields = ("item",)
    labels = {"items": "List", "item": "Each value goes in variable"}
    outputs = {"item": "", "number": "number"}  # this round's value and its count (his round 81)
    # a wire into next: the next round starts when one reaches it, while this round goes on (his round 81)
    entries = (NEXT,)
    alongside = ALWAYS  # two runs of the flow each loop their own list
    hints = {"items": "Wire into its 'next' dot to start the next round earlier: then a round can still "
                      "wait and do more while the next one runs (use the dot 'item', not the variable, there)"}

    def __init__(self, variables: VariableStore) -> None:
        super().__init__(variables)
        self.options = {"item": self.names}

    async def run(self, items: Any, item: str = "item") -> AsyncIterator[str | tuple[str, dict[str, Any]]]:
        """Checks the list first (a bad list fails the box), then hands the runner one round at a time."""
        values = to_list(items)
        self.variables.set(item, None)  # also checks the variable name before the first round

        async def rounds() -> AsyncIterator[str | tuple[str, dict[str, Any]]]:
            for number, value in enumerate(values, 1):
                self.variables.set(item, value)
                yield "each", {"item": value, "number": number}  # its orange dots while the round runs
            yield "done"

        return rounds()
