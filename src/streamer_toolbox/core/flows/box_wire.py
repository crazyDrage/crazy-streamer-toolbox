import re
from typing import Any

from streamer_toolbox.core.data.value_helpers import HELPER, apply_helper

WIRE_IN = "${box}"  # a box field that takes its value from a data wire, not wired yet
# ${box.n3} = box n3's result, ${box.n4.x} = its field x, ${box.n4.@keys} = a helper on it (value_helpers)
BOX_REF = re.compile(r"\$\{box\.(\w+)((?:\.@?\w+)*)\}")


def box_ref(node_id: str, field: str = "") -> str:
    return f"${{box.{node_id}{'.' + field if field else ''}}}"


def box_source(value: Any) -> tuple[str, str] | None:
    """(box id, field) of a wired box field, None if it isn't wired to a box."""
    match = BOX_REF.fullmatch(value) if isinstance(value, str) else None
    return (match.group(1), match.group(2).lstrip(".")) if match else None


def is_wire_in(value: Any) -> bool:
    """A box field that takes its value from a data wire (wired or not yet)."""
    return value == WIRE_IN or box_source(value) is not None


def field_of(value: Any, path: str, what: str) -> Any:
    """One field of a result: "x" of a position, "a.b" inside a field, "2" of a list (counting from 0), "@keys"
    a helper on what's there so far (value_helpers: @keys, @kinds, @count, ...)."""
    for field in filter(None, path.split(".")):
        if field.startswith(HELPER):
            value = apply_helper(field[1:], value)
        elif isinstance(value, dict) and field in value:
            value = value[field]
        elif isinstance(value, list) and field.isdigit() and int(field) < len(value):
            value = value[int(field)]
        else:
            raise KeyError(f"{what} has no field {field!r}")
    return value
