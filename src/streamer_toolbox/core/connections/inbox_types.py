import json
import logging
import threading
from pathlib import Path

from streamer_toolbox.core.files.write_whole import write_whole

log = logging.getLogger(__name__)


class InboxTypes:
    """The types that connected in at least once, per connection (his 11-21: a type is valid once it has
    connected; it can be removed again). Kept in <settings>/inbox_types.json: {"warudo": ["camera", "default"]}.
    The trigger's type list and the connection's tab show them."""

    def __init__(self, file: Path) -> None:
        self._file = file
        self._lock = threading.Lock()

    def known(self, connection_id: str) -> list[str]:
        return sorted(self._read().get(connection_id, []), key=str.casefold)

    def add(self, connection_id: str, kind: str) -> None:
        with self._lock:
            data = self._read()
            kinds = data.setdefault(connection_id, [])
            if kind not in kinds:
                kinds.append(kind)
                self._write(data)

    def remove(self, connection_id: str, kind: str) -> None:
        with self._lock:
            data = self._read()
            if kind in data.get(connection_id, []):
                data[connection_id].remove(kind)
                self._write(data)

    def _read(self) -> dict[str, list[str]]:
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except ValueError:
            log.warning("%s is broken: starting with no types", self._file)
            return {}
        return {str(k): [str(t) for t in v] for k, v in data.items() if isinstance(v, list)} \
            if isinstance(data, dict) else {}

    def _write(self, data: dict[str, list[str]]) -> None:
        write_whole(self._file, json.dumps(data, ensure_ascii=False, indent=2))
