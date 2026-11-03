import logging
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from streamer_toolbox.core.interfaces.page_opener import PageOpener
from streamer_toolbox.core.system.toolbox_restart import RESTART_EXIT_CODE
from streamer_toolbox.core.system.update_starter import UPDATE_EXIT_CODE

log = logging.getLogger(__name__)
QUICK = 15  # seconds: a restart sooner than this after its start counts as quick
QUICK_RESTARTS = 3  # that many quick ones in a row: it is broken, not restarting; the launcher gives up


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
    UPDATE_EXIT_CODE: `update` (UpdateStarter.start) starts the swap and the launcher ends; without one ready,
    the toolbox is started again as it is.
    stop() (the window's X) closes the child's stdin: it shuts down cleanly (ParentWatch) and isn't started again.
    """

    def __init__(self, command: list[str], url: str, opener: PageOpener | None = None,
                 launch: Callable[..., subprocess.Popen] = subprocess.Popen,
                 ready: Callable[[str], bool] = answers, ready_timeout: float = 60, poll: float = 0.25,
                 update: Callable[[], bool] | None = None) -> None:
        self._command = command
        self._url = url
        self._opener = opener
        self._launch = launch
        self._ready = ready
        self._ready_timeout = ready_timeout
        self._poll = poll
        self._update = update
        self._child: subprocess.Popen | None = None
        self._stopping = False
        self._restarting = False  # restart() asked: the next end starts it again whatever its code

    def run(self) -> int:
        """Until the toolbox ends without asking for a restart; its exit code."""
        opened = False
        quick = 0
        while True:
            if self._stopping:  # stopped before (or between) starts: no toolbox nobody waits for
                return 0
            started = time.monotonic()
            self._child = self._launch(self._command, stdin=subprocess.PIPE)
            if self._stopping:  # stop() came while it was being started: its stdin wasn't there yet
                self.stop()
            if not opened and self._opener is not None and self._wait_ready():
                self._opener.open(self._url)
                opened = True
            try:
                code = self._child.wait()
            except KeyboardInterrupt:  # Ctrl+C in the console reaches the child too; let it finish
                self.stop()
                code = self._child.wait()
            restart, self._restarting = self._restarting, False
            if (code == RESTART_EXIT_CODE or restart) and not self._stopping:
                quick = quick + 1 if time.monotonic() - started < QUICK and not restart else 0
                if quick >= QUICK_RESTARTS:
                    log.error("the toolbox asked for a restart %s times in a row right after starting: not "
                              "starting it again", quick)
                    return code
                log.info("restarting the toolbox")
                continue
            if code == UPDATE_EXIT_CODE and not self._stopping:
                if self._update is not None and self._update():
                    return 0  # the swap starts it again, once nothing holds the old files
                continue
            return code

    @property
    def running(self) -> bool:
        return self._child is not None and self._child.poll() is None

    def restart(self) -> None:
        """Stops the toolbox cleanly and starts it again (the starter's Restart button)."""
        self._restarting = True
        self._close_stdin()

    def stop(self) -> None:
        self._stopping = True
        self._close_stdin()

    def _close_stdin(self) -> None:
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
