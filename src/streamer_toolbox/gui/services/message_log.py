import json
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

from streamer_toolbox.core.files.write_whole import write_whole
from streamer_toolbox.gui.services.message_entry import MessageEntry

log = logging.getLogger(__name__)


class MessageLog:
    """Every message the toolbox showed, every flow run and box error, newest first (his round 81: the info bar
    and its Debug list). Memory only, up to `size` lines; the last `kept` go into `path` when the toolbox stops
    and are there again after a restart (his A3: "maybe the last 10 lines")."""

    def __init__(self, path: Path, size: int = 500, kept: int = 10) -> None:
        self._path = path
        self._kept = kept
        self._entries: deque[MessageEntry] = deque(maxlen=size)
        self.version = 0  # bumps on every add, so the lists and the bar's count know when to redraw
        self._read()

    def add(self, kind: str, text: str) -> MessageEntry:
        entry = MessageEntry(datetime.now().strftime("%H:%M:%S"), kind, text)
        self._entries.appendleft(entry)
        self.version += 1
        return entry

    def activity(self, source: str, action: str, ok: bool, result: Any) -> None:
        """An ActivityLog line (a flow or action that ran, from a trigger, Live, the API ...)."""
        text = "done" if result is None else str(result)
        self.add("run" if ok else "negative", f"{source} · {action}: {text[:300]}")

    def entries(self) -> list[MessageEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()
        self.version += 1

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            lines = [vars(e) for e in list(self._entries)[:self._kept]]
            write_whole(self._path, json.dumps(lines, ensure_ascii=False, indent=1))
        except OSError as e:
            log.warning("could not keep the last messages: %s", e)

    def _read(self) -> None:
        try:
            lines = json.loads(self._path.read_text(encoding="utf-8"))
            self._entries.extend(MessageEntry(str(x["time"]), str(x["kind"]), str(x["text"])) for x in lines)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError) as e:
            log.warning("the last messages could not be read: %s", e)
