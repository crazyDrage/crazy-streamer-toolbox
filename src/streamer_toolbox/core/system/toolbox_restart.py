from collections.abc import Callable

from streamer_toolbox.core.system.update_starter import UPDATE_EXIT_CODE

# the toolbox ends with this when it should be started again (ToolboxLauncher does that). Not 3: uvicorn ends
# with 3 when it can't start (a taken port, no console under pythonw), which then restarted it forever (11-03)
RESTART_EXIT_CODE = 75


class ToolboxRestart:
    """Stops the toolbox so its launcher starts it again (Settings → Restart): new code, flows and settings are
    read, the open pages reconnect by themselves. Only possible when a launcher runs it (start.bat and
    python -m streamer_toolbox always do). request(update=True): a downloaded update waits; the launcher puts
    it in first (UpdateStarter)."""

    def __init__(self, shutdown: Callable[[], None], available: bool) -> None:
        self._shutdown = shutdown
        self.available = available
        self.requested = False
        self.update = False

    def request(self, update: bool = False) -> None:
        if not self.available:
            raise RuntimeError("this toolbox wasn't started by its launcher, so it can't start itself again")
        self.requested = True
        self.update = update
        self._shutdown()

    @property
    def exit_code(self) -> int:
        if not self.requested:
            return 0
        return UPDATE_EXIT_CODE if self.update else RESTART_EXIT_CODE
