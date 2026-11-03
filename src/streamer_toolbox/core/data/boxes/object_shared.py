from typing import Any

from streamer_toolbox.core.data.box_value import to_kind


PAIRS = 5


def _object(value: Any) -> dict[str, Any]:
    """An empty field is an empty object; JSON text of an object is read."""
    if value is None or value == "":
        return {}
    return to_kind(value, "object")


def _key(value: Any, key: Any) -> str:
    """The key as the object has it: "LL" finds "ll" when there's no "LL" (viewers type in any case)."""
    key, whole = str(key), _object(value)
    if key in whole:
        return key
    return next((k for k in whole if str(k).casefold() == key.casefold()), key)
