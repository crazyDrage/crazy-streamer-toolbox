import json
import logging
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


class PluginSettings:
    """A plugin's settings: its defaults ship in resources/settings.json, what the streamer changes is kept in
    config/plugins/<id>.json. So updating or replacing the plugin folder never loses his changes."""

    def __init__(self, defaults: Optional[Path], saved: Path) -> None:
        self._defaults = defaults
        self._saved = saved

    def load(self) -> dict[str, Any]:
        """The defaults with his saved values on top."""
        return {**self._read(self._defaults), **self._read(self._saved)}

    def save(self, values: dict[str, Any]) -> None:
        """Keeps these values (merged into what was saved before)."""
        merged = {**self._read(self._saved), **values}
        self._saved.parent.mkdir(parents=True, exist_ok=True)
        self._saved.write_text(json.dumps(merged, indent=1, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _read(path: Optional[Path]) -> dict[str, Any]:
        if path is None or not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            log.error("%s isn't valid JSON, not used: %s", path, e)
            return {}
        return data if isinstance(data, dict) else {}
