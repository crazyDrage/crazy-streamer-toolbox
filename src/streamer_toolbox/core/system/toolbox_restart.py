from collections.abc import Callable

RESTART_EXIT_CODE = 3  # the toolbox ends with this when it should be started again (ToolboxLauncher does that)


class ToolboxRestart:
    """Stops the toolbox so its launcher starts it again (Settings → Restart): new code, flows and settings are
    read, the open pages reconnect by themselves. Only possible when a launcher runs it (start.bat and
    python -m streamer_toolbox always do)."""

    def __init__(self, shutdown: Callable[[], None], available: bool) -> None:
        self._shutdown = shutdown
        self.available = available
        self.requested = False

    def request(self) -> None:
        if not self.available:
            raise RuntimeError("this toolbox wasn't started by its launcher, so it can't start itself again")
        self.requested = True
        self._shutdown()

    @property
    def exit_code(self) -> int:
        return RESTART_EXIT_CODE if self.requested else 0
