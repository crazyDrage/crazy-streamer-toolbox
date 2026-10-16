import asyncio
from collections.abc import Callable
from typing import Any

SETTLE_SECONDS = 1.0


class VtsTrackingSettle:
    """Lets a tracking change through only when it stayed that way for a second. VTube Studio says "face lost"
    and "face found" a few hundredths of a second apart whenever the camera misses one picture (seen on his
    stream of 2026-10-11: 700 times in 3.5 hours), and each would start the "Tracking found / lost" flows."""

    def __init__(self, publish: Callable[[dict[str, Any]], None], seconds: float = SETTLE_SECONDS) -> None:
        self._publish = publish
        self._seconds = seconds
        self._told: dict[str, Any] | None = None  # what the flows heard last
        self._now: dict[str, Any] | None = None
        self._timer: asyncio.TimerHandle | None = None

    def offer(self, state: dict[str, Any]) -> None:
        """What VTube Studio says now. Needs a running loop (it is called from the connection's listener)."""
        self._now = state
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        if state != self._told:
            self._timer = asyncio.get_running_loop().call_later(self._seconds, self._settled)

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _settled(self) -> None:
        self._timer = None
        self._told = self._now
        self._publish(self._now)
