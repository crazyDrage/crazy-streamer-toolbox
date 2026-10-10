import time
from collections.abc import Callable


class LoginThrottle:
    """Slows down password guessing: after `limit` wrong tries from one address within `window` seconds, that
    address waits until the oldest of them is `window` seconds old. A right password clears its count."""

    def __init__(self, limit: int = 5, window: float = 60.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = limit
        self._window = window
        self._clock = clock
        self._failures: dict[str, list[float]] = {}

    def wait_seconds(self, address: str) -> float:
        """0 if this address may try now, else how long it has to wait."""
        now = self._clock()
        recent = [t for t in self._failures.get(address, []) if now - t < self._window]
        self._failures[address] = recent
        return 0.0 if len(recent) < self._limit else self._window - (now - recent[0])

    def failed(self, address: str) -> None:
        self._failures.setdefault(address, []).append(self._clock())

    def succeeded(self, address: str) -> None:
        self._failures.pop(address, None)
