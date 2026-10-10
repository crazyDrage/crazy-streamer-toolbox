"""Name helpers for the generated code: API keys ("userName", "Amount", "user-id") as Python names."""
import json
import keyword
import re
from typing import Any

PY_TYPES = {"text": "str", "number": "float", "yes/no": "bool", "list": "list", "object": "dict", "any": "Any"}
EMPTY = {"text": '""', "number": "0", "yes/no": "False", "any": "None"}  # list / object: default_factory


def snake(name: str) -> str:
    """"userName" / "UserName" / "user-name" / "user name" → "user_name"; a keyword or a leading digit gets an
    underscore."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name))
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    text = re.sub(r"[^0-9a-zA-Z]+", "_", text).strip("_").lower() or "value"
    if text[0].isdigit():
        text = "_" + text
    return text + "_" if keyword.iskeyword(text) else text


def camel(name: str) -> str:
    """"get_counter" → "GetCounter"."""
    return "".join(part[:1].upper() + part[1:] for part in snake(name).split("_") if part)


def unique(names: list[str]) -> list[str]:
    """The same names with _2, _3, ... where two would be equal ("userName" and "user_name")."""
    seen: dict[str, int] = {}
    out = []
    for name in names:
        seen[name] = seen.get(name, 0) + 1
        out.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    return out


def wrapped(text: str, indent: int, width: int = 116) -> str:
    """A string literal, split into several adjacent literals so no line is longer than `width`."""
    room = max(width - indent - 4, 30)
    words, parts, line = str(text).split(" "), [], ""
    for word in words:
        candidate = f"{line} {word}" if line else word
        if len(repr(candidate)) > room and line:
            parts.append(line + " ")
            line = word
        else:
            line = candidate
    parts.append(line)
    return ("\n" + " " * indent).join(_literal(p) for p in parts)


def _literal(text: str) -> str:
    """A string literal in double quotes (JSON's escapes are Python's too)."""
    return json.dumps(str(text), ensure_ascii=False)


def literal(value: Any) -> str:
    """A JSON-like value as Python source on one line, strings in double quotes (like the repo)."""
    if isinstance(value, str):
        return _literal(value)
    if isinstance(value, dict):
        return "{" + ", ".join(f"{literal(k)}: {literal(v)}" for k, v in value.items()) + "}"
    if isinstance(value, (list, tuple)):
        inner = ", ".join(literal(v) for v in value)
        return f"({inner}{',' if len(value) == 1 else ''})" if isinstance(value, tuple) else f"[{inner}]"
    return repr(value)


def block(value: Any, column: int, start: int, width: int = 118) -> str:
    """literal(value) placed at `start` (where it begins on its line); if it doesn't fit before `width`, a dict
    or list goes one item per line, items at column + 4, the closing bracket at `column`."""
    one = literal(value)
    if start + len(one) <= width or not isinstance(value, (dict, list)) or not value:
        return one
    pad = " " * (column + 4)
    if isinstance(value, dict):
        items = [f"{pad}{literal(k)}: {block(v, column + 4, column + 6 + len(literal(k)))},"
                 for k, v in value.items()]
        return "{\n" + "\n".join(items) + "\n" + " " * column + "}"
    items = [f"{pad}{block(v, column + 4, column + 4)}," for v in value]
    return "[\n" + "\n".join(items) + "\n" + " " * column + "]"


def code_dict(pairs: list[tuple[str, str]], column: int, start: int, width: int = 118) -> str:
    """{"key": code, ...} where the values are Python code (variable names), wrapped like block()."""
    one = "{" + ", ".join(f"{_literal(k)}: {code}" for k, code in pairs) + "}"
    if start + len(one) <= width:
        return one
    pad = " " * (column + 4)
    return "{\n" + "\n".join(f"{pad}{_literal(k)}: {code}," for k, code in pairs) + "\n" + " " * column + "}"
