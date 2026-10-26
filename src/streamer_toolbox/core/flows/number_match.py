"""A trigger that fits a number: any, higher than, lower than, equal to, rises above, falls below (Heart rate
changed: bpm). "Rises above" and "falls below" start once, when the number is crossed: they compare with the
event's previous_<key> as well (the heart rate before)."""
import re
from typing import Any

# how a number trigger compares: what the trigger saves in front of its number → what the editor shows
COMPARE = {"": "Any", ">": "Higher than", "<": "Lower than", "=": "Equal to", ">>": "Rises above",
           "<<": "Falls below"}
CROSSING = (">>", "<<")  # these start once, when the number is crossed
_SAVED = re.compile(r"\s*(>>|<<|>|<|=)\s*(-?\d+(?:\.\d+)?)\s*")


def compare_of(wanted: Any) -> tuple[str, float] | None:
    """A saved match like ">120" as (">", 120.0); None for anything else ("*", a name, a pattern)."""
    found = _SAVED.fullmatch(str(wanted))
    return (found.group(1), float(found.group(2))) if found else None


def to_compare(how: str, number: Any) -> str:
    """What the trigger saves: "*" for any, else the sign and the number (">120", ">>120")."""
    if how not in COMPARE or not how:
        return "*"
    try:
        number = float(number)
    except (TypeError, ValueError):
        number = 0.0
    return f"{how}{number:g}"


def fits_number(value: Any, wanted: Any, previous: Any = None) -> bool | None:
    """Whether an event's number fits a saved comparison; None when this isn't one (the value is no number,
    or the match is a plain text or pattern): then it is matched as text. A crossing (">>", "<<") also needs
    the number before (`previous`); without one it never fits."""
    compare = compare_of(wanted)
    if compare is None or not _is_number(value):
        return None
    how, number = compare
    if how in CROSSING:
        if not _is_number(previous):
            return False
        return previous <= number < value if how == ">>" else previous >= number > value
    return value > number if how == ">" else value < number if how == "<" else value == number


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
