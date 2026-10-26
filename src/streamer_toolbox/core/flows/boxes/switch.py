from typing import Any

from streamer_toolbox.core.actions.numbered_fields import numbered_fields
from streamer_toolbox.core.data.box_value import same
from streamer_toolbox.core.interfaces.box import Box

CASE = "case"  # case_1, case_2, ... (as many as it has), one output each, then "else"


class Switch(Box):
    name = "switch"
    label = "Switch"
    help = "Goes on through the first case that equals the value (a case may list several, e.g. 'ra, right_arm'), " \
           "else through 'else'. Like If, for more than two ways: + Add case for as many as you need"
    group = "If"
    ports = ("else",)
    port_fields = CASE
    flow_only = True
    hints = {"value": "What to look at, e.g. what the viewer typed", CASE: "Several words with a comma, e.g. ra, right_arm"}

    async def run(self, value: Any, **cases: Any) -> str:
        """cases: case_1, case_2, ... (and "cases", how many there are)."""
        for port in numbered_fields(CASE, cases):
            case = str(cases.get(port, ""))
            if case.strip() and any(same(value, c.strip()) for c in case.split(",")):
                return port
        return "else"
