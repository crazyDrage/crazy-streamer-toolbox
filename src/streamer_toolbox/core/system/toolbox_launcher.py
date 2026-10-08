import logging
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from streamer_toolbox.core.interfaces.page_opener import PageOpener
from streamer_toolbox.core.system.toolbox_restart import RESTART_EXIT_CODE

log = logging.getLogger(__name__)


def answers(url: str) -> bool:
    """Whether the toolbox at url answers at all (any HTTP status counts, e.g. a login redirect)."""
    try:
        urllib.request.urlopen(url, timeout=2).close()
    except urllib.error.HTTPError:
        return True
    except OSError:
        return False
    return True


class ToolboxLauncher:
    """Runs the toolbox as a child process and starts it again when it ends with RESTART_EXIT_CODE (Settings →
    Restart), so an app window stays open and only reconnects. Opens the page once, after the first start.
    stop() (the window's X) closes the child's stdin: it shuts down cleanly (ParentWatch) and isn't started again.
    """

    def __init__(self, command: list[str], url: str, opener: PageOpener | None = None,
                 launch: Callable[..., subprocess.Popen] = subprocess.Popen,
                 ready: Callable[[str], bool] = answers, ready_timeout: float = 60, poll: float = 0.25) -> None:
        self._command = command
        self._url = url
        self._opener = opener
        self._launch = launch
        self._ready = ready
        self._ready_timeout = ready_timeout
        self._poll = poll
        self._child: subprocess.Popen | None = None
        self._stopping = False

    def run(self) -> int:
        """Until the toolbox ends without asking for a restart; its exit code."""
        opened = False
        while True:
            self._child = self._launch(self._command, stdin=subprocess.PIPE)
            if not opened and self._opener is not None and self._wait_ready():
                self._opener.open(self._url)
                opened = True
            try:
                code = self._child.wait()
            except KeyboardInterrupt:  # Ctrl+C in the console reaches the child too; let it finish
                self.stop()
                code = self._child.wait()
            if code == RESTART_EXIT_CODE and not self._stopping:
                log.info("restarting the toolbox")
                continue
            return code

    def stop(self) -> None:
        self._stopping = True
        if self._child is not None and self._child.stdin is not None:
            try:
                self._child.stdin.close()
            except OSError:
                pass

    def _wait_ready(self) -> bool:
        deadline = time.monotonic() + self._ready_timeout
        while time.monotonic() < deadline and self._child.poll() is None:
            if self._ready(self._url):
                return True
            time.sleep(self._poll)
        return False
