import json
from pathlib import Path
from typing import Any

from streamer_toolbox.core.variables.variable_store import NAME_CHARS


class BoxValueFiles:
    """Values a box keeps itself (a model animation, ...) saved as files to use again in other boxes:
    <folder>/<kind>/<name>.json, one folder per kind ("vts_animation")."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def names(self, kind: str) -> list[str]:
        folder = self._folder / _checked(kind)
        return sorted((p.stem for p in folder.glob("*.json")), key=str.casefold) if folder.is_dir() else []

    def load(self, kind: str, name: str) -> Any:
        path = self._path(kind, name)
        if not path.is_file():
            raise KeyError(f"there's no saved {kind.replace('_', ' ')} {name!r}")
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, kind: str, name: str, value: Any) -> Path:
        path = self._path(kind, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _path(self, kind: str, name: str) -> Path:
        return self._folder / _checked(kind) / f"{_checked(name)}.json"


def _checked(name: str) -> str:
    """A file name of letters, digits and _ (no folders, no ..)."""
    name = name.strip().replace(" ", "_")
    if not name or not set(name) <= NAME_CHARS:
        raise ValueError(f"use letters, digits and _ for the name, not {name!r}")
    return name
