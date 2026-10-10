import threading


class FakeBrowserProcess:
    """Stands in for the app window's browser process; close() is the streamer clicking the window's X."""

    def __init__(self) -> None:
        self._closed = threading.Event()

    def close(self) -> None:
        self._closed.set()

    def wait(self) -> int:
        self._closed.wait(5)
        return 0
