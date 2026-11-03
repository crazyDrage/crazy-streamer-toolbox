import asyncio
from contextvars import ContextVar

# a Wait box's "If started again": what a new start of the flow does while the run hasn't got past this wait
ON_RETRIGGER = {"nothing": "Nothing (as the flow is set)", "restart": "Start the wait over",
                "add": "Add the time again"}


class Retrigger:
    """One run of a flow with a stretchable Wait box (light on, Wait 2 s, light off). Until that wait is over,
    starting the flow again doesn't run it a second time but pokes this run: the wait starts over or gets longer.
    Pokes that come before the wait has started are counted in when it starts."""

    def __init__(self) -> None:
        self.open = True  # False once a stretchable wait is over: from then on a new start runs as usual
        self._pokes = 0
        self._poked = asyncio.Event()

    def poke(self) -> None:
        self._pokes += 1
        self._poked.set()

    async def wait(self, seconds: float, mode: str) -> int:
        """Waits, stretched by every poke; how many pokes there were."""
        loop = asyncio.get_running_loop()
        total = self._take()
        end = loop.time() + seconds * (1 + total if mode == "add" else 1)
        try:
            while (left := end - loop.time()) > 0:
                try:
                    await asyncio.wait_for(self._poked.wait(), left)
                except TimeoutError:
                    break
                pokes = self._take()
                total += pokes
                end = loop.time() + seconds if mode == "restart" else end + seconds * pokes
        finally:
            self.open = False
        return total

    def _take(self) -> int:
        self._poked.clear()
        pokes, self._pokes = self._pokes, 0
        return pokes


# the Retrigger of the flow run this code runs in (None outside a real run), so the Wait box can find it
current_retrigger: ContextVar[Retrigger | None] = ContextVar("current_retrigger", default=None)
