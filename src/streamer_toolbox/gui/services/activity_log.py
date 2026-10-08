from collections import deque
from datetime import datetime
from typing import Any

from streamer_toolbox.gui.services.activity_entry import ActivityEntry


class ActivityLog:
    """The last runs of any action, from the GUI or the API, newest first. Memory only."""

    def __init__(self, size: int = 20) -> None:
        self._entries: deque[ActivityEntry] = deque(maxlen=size)
        self.version = 0  # bumps on every add, so pages know when to redraw

    def add(self, source: str, action: str, ok: bool, result: Any) -> None:
        text = "done" if result is None else str(result)
        self._entries.appendleft(ActivityEntry(datetime.now(), source, action, ok, text[:200]))
        self.version += 1

    def entries(self) -> list[ActivityEntry]:
        return list(self._entries)
