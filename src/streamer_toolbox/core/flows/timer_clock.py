import asyncio
import logging
import time

from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.flows.flow_library import FlowLibrary

TIMER = "timer"
log = logging.getLogger(__name__)


class TimerClock:
    """Timer triggers: a flow with the trigger {kind = "timer", every = "5"} starts every 5 seconds (like SAMMI's
    timer trigger). The clock looks at the flows' triggers on every tick, so new or edited flows count at once."""

    def __init__(self, library: FlowLibrary, events: EventBus, tick: float = 0.1) -> None:
        self._library = library
        self._events = events
        self._tick = tick
        self._due: dict[str, float] = {}
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def check(self, now: float) -> None:
        """Publishes a timer event for each interval that is due (one tick of the clock)."""
        intervals = {str(t.match.get("every", "")) for f in self._library.all() for t in f.triggers
                     if t.kind == TIMER}
        for every in intervals:
            seconds = _seconds(every)
            if seconds is None:
                continue
            due = self._due.setdefault(every, now + seconds)
            if now >= due:
                # after a stall (PC asleep), go on from now instead of firing a burst to catch up
                self._due[every] = due + seconds if due + seconds > now else now + seconds
                self._events.publish(TIMER, {"every": every})
        for every in set(self._due) - intervals:
            del self._due[every]

    async def _run(self) -> None:
        while True:
            try:
                self.check(time.monotonic())
            except Exception:
                log.exception("timer clock")
            await asyncio.sleep(self._tick)


def _seconds(text: str) -> float | None:
    try:
        seconds = float(text)
    except ValueError:
        return None
    return seconds if seconds >= 0.1 else None
