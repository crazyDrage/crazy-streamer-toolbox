from pathlib import Path
from typing import Any

import tomlkit

from streamer_toolbox.core.files.write_whole import write_whole


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
        write_whole(self._path, tomlkit.dumps(doc))

    def remove(self, table: str, keys: tuple[str, ...]) -> dict[str, Any]:
        """Takes those keys out of the table (a setting that is gone); what they held, only the ones that were
        there. Nothing is written when none was."""
        if not self._path.exists():
            return {}
        doc = tomlkit.parse(self._path.read_text(encoding="utf-8"))
        found = doc.get(table)
        if found is None:
            return {}
        removed = {key: found[key] for key in keys if key in found}
        for key in removed:
            del found[key]
        if removed:
            write_whole(self._path, tomlkit.dumps(doc))
        return {key: value.unwrap() if hasattr(value, "unwrap") else value for key, value in removed.items()}
