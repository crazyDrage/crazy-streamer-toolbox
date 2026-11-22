import asyncio
import logging
from collections.abc import Callable

from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.interfaces.connection import Connection

log = logging.getLogger(__name__)
STATUS = "connection.status"
CONNECTED, DISCONNECTED = "connected", "disconnected"


class ConnectionWatcher:
    """Starts the trigger "Status change" (his 11-21: Warudo's plugin connects in again when the toolbox tells it to,
    once Warudo is found; on connect / on disconnect / on change). Looks at every connection's status once a
    second: one that is connected now and wasn't at the last look gives `connection.status` with status
    "connected", one that was and isn't any more (closed, gone, switched off) "disconnected". Connections that
    come up with the toolbox count too (the first look knows none as connected). Cost: one look at ~25 statuses
    a second, no requests."""

    def __init__(self, connections: Callable[[], list[Connection]], events: EventBus, every: float = 1.0) -> None:
        self._connections = connections
        self._events = events
        self._every = every
        self._was: dict[str, bool] = {}
        self._task: asyncio.Task | None = None

    def check(self) -> None:
        """One look: an event for each connection that got connected or lost since the last one."""
        for connection in self._connections():
            ok = connection.status.ok
            if ok != self._was.get(connection.id, False):
                self._events.publish(STATUS, {"connection": connection.id, "title": connection.title,
                                              "status": CONNECTED if ok else DISCONNECTED})
            self._was[connection.id] = ok

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def _run(self) -> None:
        while True:
            try:
                self.check()
            except Exception:  # one odd status mustn't end the watching
                log.exception("connection watcher: a look failed")
            await asyncio.sleep(self._every)
