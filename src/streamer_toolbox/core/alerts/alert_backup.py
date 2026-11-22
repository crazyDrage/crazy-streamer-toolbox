import json
import logging
from pathlib import Path
from typing import Any

from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_store import AlertStore

log = logging.getLogger(__name__)

MIN_LOG_LINES = 100  # the log is written into the picture again after this many lines, or the line's length


class AlertBackup:
    """"Keep alerts through a restart" (his round 64 answer: off by default, a restart clears the line). With it
    on, the alert line is written down on every change: the alerts still waiting, the ones sent in the last
    minute with their numbers and the toolbox's run. After a restart the waiting alerts play, and a page that
    comes back says its last number and gets exactly what it missed (the numbers go on where they were).

    Two files, so a change costs the same at 10 or 17,000 waiting alerts (rule 28: the line has no limit):
    `alert_backup.json` is the whole line at one moment, `alert_backup.log` one short line per change since
    (an alert added, the next one shown, the line cleared). Every change has a number; the picture says the last
    one it holds, so a crash between the two files never counts a change twice. When the log is as long as the
    line, the picture is written again and the log starts over."""

    def __init__(self, path: Path, store: AlertStore, queue: AlertQueue) -> None:
        self._path = path
        self._log_path = path.with_suffix(".log")
        self._store = store
        self._queue = queue
        self._number = 0  # the newest change written down
        self._log_lines = 0

    @property
    def on(self) -> bool:
        return self._store.keep_through_restart

    def start(self) -> None:
        """At the toolbox's start (in its event loop): what was kept comes back, then every change is written."""
        if self.on and self._path.is_file():
            try:
                self._queue.restore(self._read())
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
                log.warning("the kept alerts couldn't be read (%s): starting with an empty line", e)
        self._queue.on_change = self._write_change
        self.save()

    def switch(self, on: bool) -> None:
        self._store.set_keep_through_restart(on)
        self.save()

    def save(self) -> None:
        """Off: no files. On: the whole line as it is now (written next to it first, so a crash leaves the old
        one), and an empty log."""
        if not self.on:
            self._path.unlink(missing_ok=True)
            self._log_path.unlink(missing_ok=True)
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        part = self._path.with_suffix(".part")
        part.write_text(json.dumps({**self._queue.state(), "number": self._number}, ensure_ascii=False),
                        encoding="utf-8")
        part.replace(self._path)
        self._log_path.write_text("", encoding="utf-8")
        self._log_lines = 0

    def _write_change(self, change: dict[str, Any]) -> None:
        if not self.on:
            return
        self._number += 1
        if self._log_lines >= max(MIN_LOG_LINES, self._queue.waiting):
            self.save()
            return
        with self._log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps({**change, "number": self._number}, ensure_ascii=False) + "\n")
        self._log_lines += 1

    def _read(self) -> dict[str, Any]:
        """The picture with the log's changes after it. A half-written last line (a crash) ends the log."""
        state = json.loads(self._path.read_text(encoding="utf-8"))
        self._number = int(state.get("number", 0))
        waiting = list(state.get("waiting", []))
        lines = self._log_path.read_text(encoding="utf-8").splitlines() if self._log_path.is_file() else []
        for line in lines:
            try:
                change = json.loads(line)
            except ValueError:
                break
            if int(change.get("number", 0)) <= self._number:
                continue  # already in the picture
            self._number = int(change["number"])
            if "add" in change:
                waiting.append(change["add"])
            elif "next" in change and waiting:
                waiting.pop(0)
            elif "clear" in change:
                waiting = []
            if "sent" in change:
                state["sent"], state["files"] = change["sent"], change.get("files", {})
        state["waiting"] = waiting
        return state
