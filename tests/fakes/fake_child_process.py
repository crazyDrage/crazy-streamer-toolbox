import io
import subprocess
import threading


class FakeChildProcess:
    """A toolbox process that ends with a given code; a stuck one (stuck=True) ends only when killed."""

    def __init__(self, code: int, stuck: bool = False) -> None:
        self.code = code
        self.stdin = io.BytesIO()
        self.killed = False
        self._ended = threading.Event()
        if not stuck:
            self._ended.set()

    def poll(self) -> None:
        return None

    def wait(self, timeout: float | None = None) -> int:
        if not self._ended.wait(timeout):
            raise subprocess.TimeoutExpired("toolbox", timeout)
        return self.code

    def kill(self) -> None:
        self.killed = True
        self._ended.set()
