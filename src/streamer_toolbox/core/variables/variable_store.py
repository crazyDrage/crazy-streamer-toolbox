import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
NAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
MOVED = ".old"  # what the one file of before is renamed to, once its variables are files of their own


class VariableStore:
    """The toolbox's variables, one JSON file each (config/variables/<name>.json) so they survive a restart:
    a change writes only that variable's small file, and each one can be looked at, copied or removed by itself.

    A value can be text, a number, true/false, a list or an object (e.g. a model position
    {"x": .., "y": .., "rotation": .., "size": ..}). lookup("pos.x") reads a field inside an object.

    Two names that differ only in upper and lower case (count, Count) would be one file on Windows, so the
    second one is refused. `old_file` is the one file that held all of them before (config/variables.json):
    it is taken apart once, when the folder does not exist yet, and kept next to it as variables.json.old.
    """

    def __init__(self, folder: Path, old_file: Path | None = None) -> None:
        self._folder = folder
        self._values: dict[str, Any] = {}
        self._listeners: list[Callable[[], None]] = []
        if not folder.is_dir() and old_file is not None and old_file.is_file():
            self._take_apart(old_file)
        for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
            try:
                self._values[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:  # a half-written file after a crash: the others still load
                log.warning("variable %s not read: %s", path.stem, e)

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
        twin = self._twin(name)
        if twin:
            raise ValueError(f"there is already a variable {twin!r}: {name!r} differs only in upper and lower case")
        self._write(name, value)
        self._values[name] = value
        self._tell()

    def delete(self, name: str) -> None:
        if name in self._values:
            del self._values[name]
            self._path(name).unlink(missing_ok=True)
            self._tell()

    def on_change(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def _twin(self, name: str) -> str:
        """Another variable whose name is the same but for upper and lower case, or ""."""
        return next((other for other in self._values if other != name and other.casefold() == name.casefold()), "")

    def _path(self, name: str) -> Path:
        return self._folder / f"{name}.json"

    def _write(self, name: str, value: Any) -> None:
        text = json.dumps(value, indent=2, ensure_ascii=False)  # only what fits in a file
        self._folder.mkdir(parents=True, exist_ok=True)
        half = self._path(name).with_name(f"{name}.json.tmp")
        half.write_text(text, encoding="utf-8")
        half.replace(self._path(name))

    def _tell(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _take_apart(self, old_file: Path) -> None:
        try:
            values = json.loads(old_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            log.warning("%s not read, no variable taken over: %s", old_file.name, e)
            return
        written: set[str] = set()
        for name, value in values.items() if isinstance(values, dict) else ():
            if not name or not set(name) <= NAME_CHARS or name.casefold() in written:
                log.warning("variable %r stays in %s%s only (its name can't be a file)", name, old_file.name, MOVED)
                continue
            self._write(name, value)
            written.add(name.casefold())
        self._folder.mkdir(parents=True, exist_ok=True)
        old_file.replace(old_file.with_name(old_file.name + MOVED))
