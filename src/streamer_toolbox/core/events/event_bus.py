import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger(__name__)
EventHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class EventBus:
    """Things that happen (a Twitch redeem, a timer tick) go out to everyone listening, e.g. the flow triggers.

    publish() doesn't wait for the listeners: each runs as its own task, so a slow flow never holds up the
    connection that reported the event. A failing listener is logged and doesn't affect the others.
    """

    def __init__(self, fill: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None) -> None:
        self._fill = fill  # adds what an event doesn't say itself (RoleBook: the viewer's role)
        self._handlers: list[EventHandler] = []
        self._tasks: set[asyncio.Task] = set()

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def publish(self, kind: str, data: dict[str, Any]) -> None:
        if self._fill is not None:
            data = self._fill(kind, data)
        log.debug("event %s %s", kind, data)  # timers fire every second; the activity list shows runs
        for handler in list(self._handlers):
            task = asyncio.get_running_loop().create_task(self._call(handler, kind, data))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def wait_idle(self) -> None:
        """Waits until every listener started so far is done (for tests and shutdown)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    @staticmethod
    async def _call(handler: EventHandler, kind: str, data: dict[str, Any]) -> None:
        try:
            await handler(kind, data)
        except Exception:
            log.exception("event %s: a listener failed", kind)
