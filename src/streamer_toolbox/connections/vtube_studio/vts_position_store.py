from pathlib import Path

import tomlkit

from streamer_toolbox.connections.vtube_studio.vts_position import VtsPosition


class VtsPositionStore:
    """Saved model positions per model and name, e.g. ["CrazyDrage (Ready to Rig)"]["just_chatting"].

    One file (config/vts_positions.toml), so the same name ("just_chatting") works for every model: the
    currently loaded model picks its own.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self, model: str, name: str) -> VtsPosition | None:
        entry = self._read().get(model, {}).get(name)
        return None if entry is None else VtsPosition(**{k: float(v) for k, v in entry.items()})

    def names(self, model: str) -> list[str]:
        return sorted(self._read().get(model, {}))

    def save(self, model: str, name: str, position: VtsPosition) -> None:
        doc = self._read()
        if model not in doc:
            doc[model] = tomlkit.table()
        doc[model][name] = {"x": position.x, "y": position.y, "rotation": position.rotation, "size": position.size}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    def _read(self) -> tomlkit.TOMLDocument:
        if not self._path.exists():
            return tomlkit.document()
        return tomlkit.parse(self._path.read_text(encoding="utf-8"))
