import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

NAME = "toolbox.log"
MOST_BYTES = 2 * 1024 * 1024  # one file; with the old ones kept the logs folder stays under 8 MB
OLD_FILES = 3
FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
# an entry's first line; the lines after it until the next one are its own (a traceback)
ENTRY = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+ (DEBUG|INFO|WARNING|ERROR|CRITICAL) ")
LEVELS = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR,
          "CRITICAL": logging.CRITICAL}


class LogFile:
    """What the toolbox says, also kept in a file (his 11-20: "sure", after the emotes that only showed after a
    few loads could not be looked back at: the toolbox only wrote to its console). <settings>/logs/toolbox.log,
    a few MB at most: when it is full it becomes toolbox.log.1 (the oldest of 3 goes). Every line has its time.

    Only the root logger gets the file: uvicorn sets up its own loggers when the server starts (and would drop a
    handler put on them), the failed requests come from FailedRequestLogMiddleware instead."""

    def __init__(self, folder: Path, most_bytes: int = MOST_BYTES, old_files: int = OLD_FILES) -> None:
        self.folder = folder
        self._most_bytes = most_bytes
        self._old_files = old_files

    @property
    def path(self) -> Path:
        return self.folder / NAME

    def attach(self, logger: logging.Logger | None = None) -> logging.Handler:
        """From now on the logger (the root one by default) also writes into the file."""
        self.folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(self.path, maxBytes=self._most_bytes, backupCount=self._old_files,
                                      encoding="utf-8", delay=True)
        handler.setFormatter(logging.Formatter(FORMAT))
        (logger or logging.getLogger()).addHandler(handler)
        return handler

    def entries(self, count: int = 300, least: str = "DEBUG") -> list[str]:
        """The newest `count` entries, oldest first, each with its following lines (a traceback); only those
        of level `least` or higher. Reads the older files too (toolbox.log.1, .2, ...) while there are too few."""
        floor = LEVELS.get(least.upper(), logging.DEBUG)
        found: list[str] = []
        for path in (self.path, *(self.path.with_name(f"{NAME}.{n}") for n in range(1, self._old_files + 1))):
            if len(found) >= count:
                break
            found = [entry for entry in _entries(path) if _level(entry) >= floor] + found
        return found[-count:]


def _entries(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    entries: list[str] = []
    for line in lines:
        if ENTRY.match(line) or not entries:
            entries.append(line)
        else:
            entries[-1] += "\n" + line
    return entries


def _level(entry: str) -> int:
    found = ENTRY.match(entry)
    return LEVELS[found.group(1)] if found else logging.INFO
