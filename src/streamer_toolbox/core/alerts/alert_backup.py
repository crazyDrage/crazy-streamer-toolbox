import json
import logging
from pathlib import Path

from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_store import AlertStore

log = logging.getLogger(__name__)


class AlertBackup:
    """"Keep alerts through a restart" (his round 64 answer: off by default, a restart clears the line). With it
    on, the alert line is written to a file on every change: the alerts still waiting, the ones sent in the last
    minute with their numbers and the toolbox's run. After a restart the waiting alerts play, and a page that
    comes back says its last number and gets exactly what it missed (the numbers go on where they were)."""

    def __init__(self, path: Path, store: AlertStore, queue: AlertQueue) -> None:
        self._path = path
        self._store = store
        self._queue = queue

    @property
    def on(self) -> bool:
        return self._store.keep_through_restart

    def start(self) -> None:
        """At the toolbox's start (in its event loop): what was kept comes back, then every change is written."""
        if self.on and self._path.is_file():
            try:
                self._queue.restore(json.loads(self._path.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError, KeyError) as e:
                log.warning("the kept alerts couldn't be read (%s): starting with an empty line", e)
        self._queue.on_change = self.save
        self.save()

    def switch(self, on: bool) -> None:
        self._store.set_keep_through_restart(on)
        self.save()

    def save(self) -> None:
        """Off: no file. On: the line as it is now (written next to it first, so a crash leaves the old one)."""
        if not self.on:
            self._path.unlink(missing_ok=True)
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        part = self._path.with_suffix(".part")
        part.write_text(json.dumps(self._queue.state(), ensure_ascii=False), encoding="utf-8")
        part.replace(self._path)
