import json
from pathlib import Path


class FlowFolders:
    """What a folder of flows has besides its flows (a folder exists while a flow is in it; this keeps its
    settings when it is empty for a moment): whether it is hidden in the list (his "hide in list" of
    2026-10-29: with many flows, e.g. the alerts' own, the list stays short) and whether it is switched off
    (his "disable the whole folder", same day: none of its flows starts, whatever each one's own switch says).
    In flow_folders.json, next to the flows folder."""

    def __init__(self, path: Path) -> None:
        self._path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        self._hidden = {str(name) for name in data.get("hidden", [])}
        self._off = {str(name) for name in data.get("off", [])}

    def hidden(self, folder: str) -> bool:
        return bool(folder) and folder in self._hidden

    def all_hidden(self) -> set[str]:
        return set(self._hidden)

    def off(self, folder: str) -> bool:
        return bool(folder) and folder in self._off

    def set_off(self, folder: str, on: bool) -> None:
        """on: the folder is switched off."""
        if not folder or self.off(folder) == on:
            return
        (self._off.add if on else self._off.discard)(folder)
        self._write()

    def set_hidden(self, folder: str, on: bool) -> None:
        if not folder or self.hidden(folder) == on:
            return
        (self._hidden.add if on else self._hidden.discard)(folder)
        self._write()

    def renamed(self, old: str, new: str) -> None:
        """A folder got another name: its settings go along ("" = it is gone)."""
        for names in (self._hidden, self._off):
            if old in names:
                names.discard(old)
                if new:
                    names.add(new)
        self._write()

    def _write(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"hidden": sorted(self._hidden, key=str.casefold),
                                          "off": sorted(self._off, key=str.casefold)}, indent=2,
                                         ensure_ascii=False), encoding="utf-8")
