import json
from collections.abc import Callable
from typing import Any

from streamer_toolbox.core.data.box_value import kind_of, understand

HELPER = "@"  # a wire path part like "@keys" is a helper, never a real key: ${box.n3.@kinds}


def _keys(value: Any) -> list[str]:
    return list(_object(value, "keys"))


def _values(value: Any) -> list[Any]:
    return list(_object(value, "values").values())


def _kinds(value: Any) -> dict[str, str] | list[str]:
    if isinstance(value, list):
        return [kind_of(v) for v in value]
    return {key: kind_of(v) for key, v in _object(value, "kinds").items()}


def _count(value: Any) -> int:
    if isinstance(value, (list, dict, str)):
        return len(value)
    raise ValueError(f"@count needs a list, an object or text, not {kind_of(value)}")


def _first(value: Any) -> Any:
    return _list(value, "first")[0]


def _last(value: Any) -> Any:
    return _list(value, "last")[-1]


def _text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


# name → (what it gives, its kind, the kinds it works on (() = any), how): offered on the orange outputs in a
# field's "from box" list (on an output of a known kind only the helpers that fit it)
HELPERS: dict[str, tuple[str, str, tuple[str, ...], Callable[[Any], Any]]] = {
    "keys": ("its keys", "list", ("object",), _keys),
    "values": ("its values", "list", ("object",), _values),
    "kinds": ("each key's kind", "object", ("object", "list"), _kinds),
    "count": ("how many", "number", ("object", "list"), _count),
    "kind": ("what it is", "text", (), kind_of),
    "first": ("first item", "", ("list",), _first),
    "last": ("last item", "", ("list",), _last),
    "text": ("as text", "text", ("object", "list"), _text),
}


def helpers_for(kind: str) -> list[str]:
    """The helpers that make sense on a value of that kind ("" = not known: all of them). One text, number or
    yes/no has none: there is nothing in it to count or pick, and its kind is known already."""
    if not kind or kind == "any":
        return list(HELPERS)
    return [name for name, (_, _, fits, _) in HELPERS.items() if kind in fits]


def apply_helper(name: str, value: Any) -> Any:
    """What helper @name gives for value: @keys of {"x": 1, "y": 2} → ["x", "y"], @kinds → {x: number, ...}."""
    if name not in HELPERS:
        raise KeyError(f"unknown helper @{name}; there are {', '.join('@' + h for h in HELPERS)}")
    return HELPERS[name][3](understand(value))


def _object(value: Any, helper: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"@{helper} needs an object, not {kind_of(value)}")
    return value


def _list(value: Any, helper: str) -> list:
    if not isinstance(value, list) or not value:
        raise ValueError(f"@{helper} needs a list with something in it, not {kind_of(value)}"
                         + (" (empty)" if value == [] else ""))
    return value
