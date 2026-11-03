import subprocess
import threading
from collections.abc import Callable


class TiedToolbox:
    """The test toolbox, started by the test window and tied to it both ways (his note of 10-30: "Nothing should
    stay alive after the software is closed"). It runs with --tied: it stops when its stdin ends, which happens
    when stop() closes it and also when the test window's process is gone in any other way (Ctrl+C, the console
    closed, a crash). When the toolbox ends by itself (its app window closed), on_gone is called, so the test
    window stops too.

    Before this, test-window.bat started it with `start /b`, which switches Ctrl+C off for it: the batch ended
    and the toolbox stayed running without a window."""

    def __init__(self, command: list[str], env: dict[str, str] | None = None,
                 launch: Callable[..., subprocess.Popen] = subprocess.Popen, stop_wait: float = 15) -> None:
        self._command = command
        self._env = env
        self._launch = launch
        self._stop_wait = stop_wait
        self._process: subprocess.Popen | None = None
        self._stopping = False

    def start(self, on_gone: Callable[[], None]) -> None:
        self._process = self._launch(self._command, stdin=subprocess.PIPE, env=self._env)
        threading.Thread(target=self._watch, args=(on_gone,), name="tied-toolbox", daemon=True).start()

    def stop(self) -> None:
        """Closes its stdin and waits until it has ended (killed if it doesn't within stop_wait seconds)."""
        self._stopping = True
        process = self._process
        if process is None or process.poll() is not None:
            return
        try:
            process.stdin.close()
        except OSError:
            pass
        try:
            process.wait(self._stop_wait)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def _watch(self, on_gone: Callable[[], None]) -> None:
        self._process.wait()
        try:
            self._process.stdin.close()
        except OSError:
            pass
        if not self._stopping:
            on_gone()
