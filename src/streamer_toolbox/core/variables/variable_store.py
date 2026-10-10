import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

NAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


class VariableStore:
    """The toolbox's variables, kept in one JSON file (config/variables.json) so they survive a restart.

    A value can be text, a number, true/false, a list or an object (e.g. a model position
    {"x": .., "y": .., "rotation": .., "size": ..}). lookup("pos.x") reads a field inside an object.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._values: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self._listeners: list[Callable[[], None]] = []

    def all(self) -> dict[str, Any]:
        return dict(sorted(self._values.items(), key=lambda kv: kv[0].casefold()))

    def names(self) -> list[str]:
        return list(self.all())

    def get(self, name: str, default: Any = None) -> Any:
        return self._values.get(name, default)

    def lookup(self, path: str) -> Any:
        """"pos" → the whole value, "pos.x" → its field x. Raises KeyError if something is missing."""
        name, *fields = path.split(".")
        if name not in self._values:
            raise KeyError(f"no variable {name!r}")
        value = self._values[name]
        for field in fields:
            if not isinstance(value, dict) or field not in value:
                raise KeyError(f"variable {name!r} has no field {field!r}")
            value = value[field]
        return value

    def set(self, name: str, value: Any) -> None:
        if not name or not set(name) <= NAME_CHARS:
            raise ValueError(f"variable name {name!r}: use only letters, digits and _")
        json.dumps(value)  # only what fits in the file
        self._values[name] = value
        self._save()

    def delete(self, name: str) -> None:
        if self._values.pop(name, None) is not None:
            self._save()

    def on_change(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._values, indent=2, ensure_ascii=False), encoding="utf-8")
        for listener in list(self._listeners):
            listener()
