from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.data.box_value import to_number
from streamer_toolbox.core.interfaces.box import Box

MATH = ["+", "-", "*", "/"]


class Calculate(Box):
    name = "math"
    label = "Calculate"
    help = "a + - * / b (plus, minus, times, divided by), e.g. the model's x minus 0.2 to move it left. Wire a " \
           "number into a (or b), and this box's result into the next box"
    group = "Math"
    options = {"op": fixed_choices(MATH)}
    flow_only = True
    data_only = True  # no run wire: it runs whenever a box needs its value (his OPEN 92)
    labels = {"a": "First number", "op": "Sign", "b": "Second number"}

    async def run(self, a: float, op: str = "+", b: float = 0) -> float:
        return work_out(a, op, b)


def work_out(a: Any, op: str, b: Any) -> float:
    """a op b, a whole number when it is one (also Math on variable's)."""
    x, y = to_number(a), to_number(b)
    if x is None or y is None:
        raise ValueError(f"Calculate needs two numbers, got {a!r} and {b!r}")
    if op not in MATH:
        raise ValueError(f"unknown sign {op!r}; use one of {' '.join(MATH)}")
    if op == "/" and y == 0:
        raise ValueError("can't divide by 0")
    result = {"+": x + y, "-": x - y, "*": x * y, "/": x / y if y else 0.0}[op]
    return int(result) if result == int(result) else round(result, 10)
