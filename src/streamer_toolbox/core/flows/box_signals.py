import asyncio
from contextvars import ContextVar

_CURRENT: ContextVar["BoxSignals | None"] = ContextVar("box_signals", default=None)
# a box with entries reached while it already runs (in another run of the flow): its `alongside` field says
ONE, ALONGSIDE = "one", "alongside"
ON_ALREADY_RUNNING = {ONE: "Only one: a new start stops here", ALONGSIDE: "Another one alongside"}


class BoxSignals:
    """What arrived at a running box's extra run dots (its entries, e.g. a Loop's "stop") from other runs of the
    flow. The runner makes one per running box and hands it to the box's action through current() (set while the
    box runs), so the action's parameters stay as they are; outside a flow (Test box, API) current() is None."""

    def __init__(self) -> None:
        self._arrived: set[str] = set()
        self._changed = asyncio.Event()

    @staticmethod
    def current() -> "BoxSignals | None":
        return _CURRENT.get()

    def use(self) -> None:
        """Makes this the current() of the running task (the runner, right before it calls the box)."""
        _CURRENT.set(self)

    def send(self, entry: str) -> None:
        self._arrived.add(entry)
        self._changed.set()

    def has(self, *entries: str) -> bool:
        """True if one of the entries arrived."""
        return any(entry in self._arrived for entry in entries)

    async def wait_for(self, seconds: float, *entries: str) -> bool:
        """Waits up to seconds; True as soon as one of the entries arrived (also if it had before)."""
        try:
            async with asyncio.timeout(seconds):
                while not self.has(*entries):
                    self._changed.clear()
                    await self._changed.wait()
        except TimeoutError:
            pass
        return self.has(*entries)
