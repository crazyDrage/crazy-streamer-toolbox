import json
import logging
import time
from collections.abc import Callable, MutableMapping
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
KEEP_DAYS = 30  # day files older than this are removed at start
SKIPPED = frozenset({"timer"})  # ticks every second and says nothing new
ON_KEY = "event_recording"  # in `choice`: True while it records


class EventRecording:
    """Every event of a stream, one line each, in a file per day: `<folder>/2026-10-11.jsonl` with
    {"trigger", "at", "data", "raw"}. `data` is what a flow's Start box got; `raw` is the message as the
    platform sent it, where the connection hands it over (raw()). LastEvents keeps only the newest event of
    each trigger; this keeps all of them, so a stream can be looked at afterwards and used as test data.

    Off until it is switched on (Settings → Event recording); the switch counts from the next event, without
    a restart. `choice` keeps it (the GUI's general storage). The files stay on this PC. Chat messages are in
    them."""

    def __init__(self, folder: Path, choice: MutableMapping[str, Any], clock: Callable[[], float] = time.time) -> None:
        self._folder = folder
        self._choice = choice
        self._clock = clock
        self._raw: dict[str, Any] = {}
        self._tidy()

    @property
    def on(self) -> bool:
        return self._choice.get(ON_KEY) is True

    def set_on(self, on: bool) -> None:
        self._choice[ON_KEY] = bool(on)

    @property
    def folder(self) -> Path:
        return self._folder

    def size(self) -> tuple[int, int]:
        """How many day files there are, and their bytes together."""
        sizes = [file.stat().st_size for file in self._folder.glob("????-??-??.jsonl")]
        return len(sizes), sum(sizes)

    def raw(self, kind: str, message: Any) -> None:
        """The platform's own message for the event that is published next under this name."""
        if self.on:
            self._raw[kind] = message

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        raw = self._raw.pop(kind, None)
        if kind in SKIPPED or not self.on:
            return
        now = datetime.fromtimestamp(self._clock()).astimezone()
        entry = {"trigger": kind, "at": now.isoformat(timespec="milliseconds"), "data": data}
        if raw is not None:
            entry["raw"] = raw
        try:
            self._folder.mkdir(parents=True, exist_ok=True)
            with self.path(now).open("a", encoding="utf-8") as file:
                file.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except OSError as e:  # a full or locked disk must not stop the stream
            log.warning("event %s not recorded: %s", kind, e)

    def path(self, day: datetime) -> Path:
        return self._folder / f"{day:%Y-%m-%d}.jsonl"

    def _tidy(self) -> None:
        oldest = f"{datetime.fromtimestamp(self._clock() - KEEP_DAYS * 86400):%Y-%m-%d}"
        for file in self._folder.glob("????-??-??.jsonl"):
            if file.stem < oldest:
                try:
                    file.unlink()
                except OSError as e:
                    log.warning("old recording %s not removed: %s", file.name, e)
