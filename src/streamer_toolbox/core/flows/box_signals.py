import asyncio
from contextvars import ContextVar

_CURRENT: ContextVar["BoxSignals | None"] = ContextVar("box_signals", default=None)


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

    def has(self, entry: str) -> bool:
        return entry in self._arrived

    async def wait_for(self, entry: str, seconds: float) -> bool:
        """Waits up to seconds; True as soon as entry arrived (also if it had before)."""
        try:
            async with asyncio.timeout(seconds):
                while not self.has(entry):
                    self._changed.clear()
                    await self._changed.wait()
        except TimeoutError:
            pass
        return self.has(entry)
