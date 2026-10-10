from pathlib import Path
from typing import Any

import tomlkit


class ConfigTableWriter:
    """Saves keys into one [table] of toolbox.toml, keeping every other line, table and comment.

    Creates the file when it doesn't exist yet; without other tables the toolbox keeps its defaults.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, table: str, values: dict[str, Any]) -> None:
        """Sets each key; a None value leaves that key as it is."""
        doc = tomlkit.parse(self._path.read_text(encoding="utf-8")) if self._path.exists() else tomlkit.document()
        if table not in doc:
            doc[table] = tomlkit.table()
        for key, value in values.items():
            if value is not None:
                doc[table][key] = value
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(tomlkit.dumps(doc), encoding="utf-8")
