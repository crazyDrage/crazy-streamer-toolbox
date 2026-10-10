import json
import time
from pathlib import Path

DEFAULT_FOLDER = Path.home() / ".veadotube" / "instances"
FRESH = 10.0  # veadotube's own limit: a file whose time is older belongs to a program that is gone


class VeadotubeInstances:
    """Where a running veadotube listens. Each running program keeps a small file in veadotube's instances
    folder, named by its id ("mini-<start time>-<process id>"), holding {"time", "name", "id", "version",
    "language", "server"} and written again every few seconds; `server` is its websocket address (e.g.
    "127.0.0.1:2424").

    The folder is ~/.veadotube/instances on every system (veado.tube/docs/tech/data: the data folder is
    `%USERPROFILE%\\.veadotube` on Windows). The address can also be typed on the connection's tab."""

    def __init__(self, folder: Path = DEFAULT_FOLDER) -> None:
        self._folder = folder

    def address(self, kind: str = "mini") -> str:
        """The websocket address of the running veadotube that wrote last; "" when none runs."""
        best, address = 0.0, ""
        if not self._folder.is_dir():
            return ""
        for file in self._folder.iterdir():
            if not file.is_file() or not file.name.startswith(kind + "-"):
                continue
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                written, server = float(data["time"]), str(data["server"])
            except (OSError, ValueError, KeyError, TypeError):
                continue
            if server and written > best and time.time() - written <= FRESH:
                best, address = written, server
        return address
