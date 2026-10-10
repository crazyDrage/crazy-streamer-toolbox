import json
import math
from typing import Any


def to_list(value: Any) -> list[Any]:
    """A box field as a list: a list stays one, JSON text of a list is read, an empty field is an empty list."""
    if isinstance(value, list):
        return list(value)
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            parsed = None
        if isinstance(parsed, list):
            return parsed
    raise ValueError(f"{value!r} is not a list")


def to_bool(value: Any) -> bool:
    """A box field may hold "false" as text."""
    if isinstance(value, str):
        return value.strip().casefold() not in ("false", "0", "no", "off", "")
    return bool(value)


def same(a: Any, b: Any) -> bool:
    """Equal the way the If box sees it: numbers by value ("3" is 3), text without caring about upper/lower case."""
    if isinstance(a, (dict, list)) or isinstance(b, (dict, list)):
        return a == b
    x, y = _whole(a), _whole(b)
    if x is None or y is None:  # two whole numbers are compared exactly: long ids differ in their last digits
        x, y = _number(a), _number(b)
    if x is not None and y is not None:
        return x == y
    return str(a).casefold() == str(b).casefold()


def _whole(value: Any) -> int | None:
    """A whole number with every digit (a float keeps about 15: an 18 digit id would get other last digits)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = value.strip() if isinstance(value, str) else ""
    return int(text) if text.removeprefix("-").removeprefix("+").isdecimal() and text.isascii() else None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


KINDS = ("number", "text", "yes/no", "list", "object", "any")


def kind_of(value: Any) -> str:
    """What a value is, the way Split data shows it: a number, text, yes/no, list or object. A value keeps the
    kind it came with: text that looks like a number ("3", an id) is text. Only what is typed by hand is read
    for what it holds (understand; RegisteredAction.typed)."""
    if isinstance(value, bool):
        return "yes/no"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "text" if isinstance(value, str) else "any"


def understand(value: Any) -> Any:
    """Text as what it holds: "3" → 3, "1.5" → 1.5, "true" → True, JSON text → a list or object; else as is."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.casefold() in ("true", "false"):
        return text.casefold() == "true"
    if text[:1] in ("{", "["):
        try:
            return json.loads(text)
        except ValueError:
            return value
    digits = text.removeprefix("-")
    if text[:1] == "+" or (digits[:1] == "0" and digits[1:2].isdigit()):
        return value  # "007", "+49": an id or a phone number, not a number (0, 0.5 and -0.5 still are)
    whole = _whole(text)
    if whole is not None:
        return whole
    number = _number(text)
    if number is None or not math.isfinite(number):
        return value
    return int(number) if number == int(number) and "." not in text and "e" not in text.casefold() else number


def to_kind(value: Any, kind: str) -> Any:
    """A value as the given kind (see KINDS); fails if it can't be one."""
    if kind == "number":
        whole, number = _whole(value), _number(value)
        if number is None:
            raise ValueError(f"{value!r} is not a number")
        return whole if whole is not None else int(number) if number.is_integer() else number
    if kind == "text":
        return value if isinstance(value, str) else json.dumps(value) if isinstance(value, (dict, list)) \
            else str(value)
    if kind == "yes/no":
        return to_bool(value)
    if kind == "list":
        return to_list(value)
    if kind == "object":
        value = understand(value)
        if not isinstance(value, dict):
            raise ValueError(f"{value!r} is not an object")
        return value
    return value
