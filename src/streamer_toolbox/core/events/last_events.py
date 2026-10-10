import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class LastEvents:
    """The last time each trigger fired, kept as a file: `<folder>/<trigger>.json` (twitch.gift.json) with
    {"trigger", "at", "data", "raw"}. `data` is what a flow's Start box got; `raw` is the message as the
    platform sent it, where the connection hands it over (raw()). So a trigger that is hard to make happen
    (gift subs) can be looked at afterwards, and the flow editor's test run starts with its values.

    A file is written at most once per `delay` seconds per trigger (the newest one wins), and not at all when
    the data is the same as last time (a timer ticking every second writes once)."""

    def __init__(self, folder: Path, delay: float = 5.0) -> None:
        self._folder = folder
        self._delay = delay
        self._raw: dict[str, Any] = {}
        self._waiting: dict[str, dict[str, Any]] = {}  # trigger → the entry that is written next
        self._written: dict[str, Any] = {}  # trigger → the data in its file
        self._timers: dict[str, asyncio.TimerHandle] = {}

    def raw(self, kind: str, message: Any) -> None:
        """The platform's own message for the event that is published next under this name."""
        self._raw[kind] = message

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        newest = self._waiting[kind]["data"] if kind in self._waiting else self._written.get(kind)
        if newest == data:
            return
        entry = {"trigger": kind, "at": datetime.now().astimezone().isoformat(timespec="seconds"), "data": data}
        if kind in self._raw:
            entry["raw"] = self._raw.pop(kind)
        self._waiting[kind] = entry
        if kind not in self._timers:
            self._timers[kind] = asyncio.get_running_loop().call_later(self._delay, self._write, kind)

    def get(self, kind: str) -> dict[str, Any] | None:
        """The data of the trigger's last event, also from before a restart; None if it never fired."""
        if kind in self._waiting:
            return self._waiting[kind]["data"]
        try:
            data = json.loads(self.path(kind).read_text(encoding="utf-8")).get("data")
        except (OSError, ValueError, AttributeError):
            return None
        return data if isinstance(data, dict) else None

    def path(self, kind: str) -> Path:
        return self._folder / (re.sub(r"[^\w.-]", "_", kind) + ".json")

    def flush(self) -> None:
        """Writes what is still waiting (at shutdown)."""
        for kind in list(self._waiting):
            self._write(kind)

    def _write(self, kind: str) -> None:
        timer = self._timers.pop(kind, None)
        if timer is not None:
            timer.cancel()
        entry = self._waiting.pop(kind, None)
        if entry is None:
            return
        path = self.path(kind)
        try:
            self._folder.mkdir(parents=True, exist_ok=True)
            half = path.with_name(path.name + ".tmp")
            half.write_text(json.dumps(entry, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            half.replace(path)
        except OSError as e:
            log.warning("last event of %s not saved: %s", kind, e)
            return
        self._written[kind] = entry["data"]
