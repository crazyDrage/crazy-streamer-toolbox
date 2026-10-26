from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.data.box_value import to_number
from streamer_toolbox.core.interfaces.box import Box

OPERATORS = ["==", "!=", "contains", "<", ">", "<=", ">="]


class IfBox(Box):
    """If: then or else. (IfBox, not If: the file can't be called if.py.)"""

    name = "if"
    label = "If"
    help = "Goes on through 'then' if the check is true, else through 'else'. Text is compared without caring " \
           "about upper/lower case"
    group = "If"
    options = {"op": fixed_choices(OPERATORS)}
    ports = ("then", "else")
    flow_only = True
    labels = {"left": "Value", "op": "Check", "right": "Compare with"}
    hints = {"op": "contains = the text is somewhere in it; < > need two numbers"}

    async def run(self, left: Any, op: str = "==", right: Any = "") -> bool:
        if op not in OPERATORS:
            raise ValueError(f"unknown check {op!r}; use one of {', '.join(OPERATORS)}")
        if op == "contains":
            return str(right).casefold() in str(left).casefold()
        a, b = to_number(left), to_number(right)
        if a is None or b is None:  # text: only equal / not equal make sense
            a, b = str(left).casefold(), str(right).casefold()
        checks = {"==": a == b, "!=": a != b}
        if op in checks:
            return checks[op]
        if isinstance(a, str):
            raise ValueError(f"{op} needs two numbers, got {left!r} and {right!r}")
        return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
