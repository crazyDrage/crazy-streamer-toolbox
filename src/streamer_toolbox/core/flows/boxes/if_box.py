from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.data.box_value import to_number
from streamer_toolbox.core.interfaces.box import Box

OPERATORS = ["==", "!=", "contains", "starts with", "ends with", "<", ">", "<=", ">="]
TEXT_CHECKS = {"contains": str.__contains__, "starts with": str.startswith, "ends with": str.endswith}


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
    labels = {"left": "Value", "op": "Check", "right": "Compare with", "ignore_case": "Ignore case"}
    hints = {"op": "contains = the text is somewhere in it; starts with / ends with = it begins / ends with it; "
                   "< > need two numbers",
             "ignore_case": "On: Twitch, twitch and TWITCH are the same text. Off: upper/lower case must match "
                            "(his round 90)"}

    async def run(self, left: Any, op: str = "==", right: Any = "", ignore_case: bool = True) -> bool:
        """ignore_case: on by default, as text was always compared before the switch came (his round 90)."""
        if op not in OPERATORS:
            raise ValueError(f"unknown check {op!r}; use one of {', '.join(OPERATORS)}")
        text = (lambda value: str(value).casefold()) if ignore_case else str
        if op in TEXT_CHECKS:  # starts with / ends with: his notes of 10-29
            return TEXT_CHECKS[op](text(left), text(right))
        a, b = to_number(left), to_number(right)
        if a is None or b is None:  # text: only equal / not equal make sense
            a, b = text(left), text(right)
        checks = {"==": a == b, "!=": a != b}
        if op in checks:
            return checks[op]
        if isinstance(a, str):
            raise ValueError(f"{op} needs two numbers, got {left!r} and {right!r}")
        return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
