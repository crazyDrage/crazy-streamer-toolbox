import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_skipped import FlowSkipped
from streamer_toolbox.core.flows.retrigger import Retrigger, current_retrigger

# what a flow does when it's started again while it still runs (SAMMI: overlappable / queueable / neither)
WHEN_BUSY = {"alongside": "Run alongside", "queue": "Wait in line", "skip": "Skip"}


class FlowGate:
    """Keeps track of which flows are running and lets a new run of the same flow go alongside, wait until the
    running one is done (one after the other, in the order they came), or not run at all.

    A flow with a stretchable Wait box (If started again: start over / add time) comes first: while a run hasn't
    got past that wait, a new start stretches the wait instead of running (see Retrigger)."""

    def __init__(self, stretchable: Callable[[Flow], bool] = lambda flow: False) -> None:
        self._stretchable = stretchable  # FlowRunner: has a switched-on box with a stretchable wait
        self._running: dict[str, int] = {}
        self._lines: dict[str, asyncio.Lock] = {}
        self._retriggers: dict[str, list[Retrigger]] = {}

    def stretch(self, flow: Flow) -> bool:
        """True if a running run of the flow took this start to stretch its wait (then don't run it)."""
        waiting = [r for r in self._retriggers.get(flow.name, []) if r.open]
        for retrigger in waiting:
            retrigger.poke()
        return bool(waiting)

    @asynccontextmanager
    async def enter(self, flow: Flow) -> AsyncIterator[None]:
        """Raises FlowSkipped for a "skip" flow that is already running."""
        if flow.when_busy == "skip" and self._running.get(flow.name):
            raise FlowSkipped(f"flow {flow.label!r} is still running, so this start was skipped")
        line = self._lines.setdefault(flow.name, asyncio.Lock()) if flow.when_busy == "queue" else None
        if line is not None:
            await line.acquire()
        self._running[flow.name] = self._running.get(flow.name, 0) + 1
        retrigger = Retrigger() if self._stretchable(flow) else None
        if retrigger is not None:
            self._retriggers.setdefault(flow.name, []).append(retrigger)
        token = current_retrigger.set(retrigger)  # also None, so a flow used as a box doesn't see the outer one
        try:
            yield
        finally:
            current_retrigger.reset(token)
            if retrigger is not None:
                self._retriggers[flow.name].remove(retrigger)
            self._running[flow.name] -= 1
            if line is not None:
                line.release()

    def is_running(self, name: str) -> bool:
        return bool(self._running.get(name))

