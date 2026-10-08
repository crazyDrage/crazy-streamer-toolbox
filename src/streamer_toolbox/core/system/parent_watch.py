import os
import threading
from collections.abc import Callable


class ParentWatch:
    """In a toolbox the launcher started: the launcher holds our stdin open. When it closes it (the app window's X,
    Ctrl+C) or the launcher itself is gone, stdin ends and the toolbox shuts down cleanly (no toolbox left running
    without a window).

    Reads the raw file descriptor (os.read): a thread blocked in sys.stdin's buffered reader makes Python crash
    at interpreter shutdown ("could not acquire lock for <stdin>")."""

    def __init__(self, fd: int, on_gone: Callable[[], None]) -> None:
        self._fd = fd
        self._on_gone = on_gone

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self._watch, name="parent-watch", daemon=True)
        thread.start()
        return thread

    def _watch(self) -> None:
        try:
            while os.read(self._fd, 1024):
                pass  # the launcher never writes; anything sent is ignored
        except OSError:
            pass
        self._on_gone()
