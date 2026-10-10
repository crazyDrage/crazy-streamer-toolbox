"""A trigger that fits a number: any, higher than, lower than, equal to (Heart rate changed: bpm)."""
import re
from typing import Any

# how a number trigger compares: what the trigger saves in front of its number → what the editor shows
COMPARE = {"": "Any", ">": "Higher than", "<": "Lower than", "=": "Equal to"}
_SAVED = re.compile(r"\s*(>|<|=)\s*(-?\d+(?:\.\d+)?)\s*")


def compare_of(wanted: Any) -> tuple[str, float] | None:
    """A saved match like ">120" as (">", 120.0); None for anything else ("*", a name, a pattern)."""
    found = _SAVED.fullmatch(str(wanted))
    return (found.group(1), float(found.group(2))) if found else None


def to_compare(how: str, number: Any) -> str:
    """What the trigger saves: "*" for any, else the sign and the number (">120")."""
    if how not in (">", "<", "="):
        return "*"
    try:
        number = float(number)
    except (TypeError, ValueError):
        number = 0.0
    return f"{how}{number:g}"


def fits_number(value: Any, wanted: Any) -> bool | None:
    """Whether an event's number fits a saved comparison; None when this isn't one (the value is no number,
    or the match is a plain text or pattern): then it is matched as text."""
    compare = compare_of(wanted)
    if compare is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    how, number = compare
    return value > number if how == ">" else value < number if how == "<" else value == number
