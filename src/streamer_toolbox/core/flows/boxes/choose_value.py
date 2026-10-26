from typing import Any

from streamer_toolbox.core.interfaces.box import Box


class ChooseValue(Box):
    name = "choose"
    label = "Choose value"
    help = "Gives the value of the line its run wire came in at, then goes on: each line has a run dot and a value " \
           "of its own, e.g. an If's then into line 1, its else into line 2, and the next box gets the value of the " \
           "side that ran. + Add value for more lines"
    group = "If"
    flow_only = True
    entry_fields = "value"
    typed = ("value",)
    hints = {"value": "The value this line gives; its run dot is the one on its left"}

    async def run(self, value: Any = "") -> Any:
        """The value of the line it was started at (the runner hands only that one over)."""
        return value
