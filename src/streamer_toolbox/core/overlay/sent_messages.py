import secrets
import time
from collections import deque
from collections.abc import Callable
from typing import Any


class SentMessages:
    """The last messages the toolbox sent to overlay pages (the alerts, a widget), each with a number ("id"). A
    page remembers the last number it got; when it comes back after its line broke it says that number, and gets
    what it missed (his round 64 idea).

    The numbers belong to this run of the toolbox (`run`): a page that comes back after a restart says another
    run and gets everything kept from this one. Only messages younger than max_age seconds go out again: an alert
    from long ago would show out of place. An alert is 0.3-1.5 KB: the 1000 kept are about 1.5 MB of memory."""

    def __init__(self, max_age: float, keep: int = 1000, clock: Callable[[], float] = time.monotonic) -> None:
        self.run = secrets.token_hex(4)
        self.last = 0
        self._max_age = max_age
        self._clock = clock
        self._kept: deque[tuple[float, str | None, dict[str, Any]]] = deque(maxlen=keep)  # (sent at, to, message)

    def stamp(self, message: dict[str, Any], to: str | None = None) -> dict[str, Any]:
        """The message with its number, kept. to: the one widget it is for (None: every page)."""
        self.last += 1
        stamped = {**message, "id": self.last}
        self._kept.append((self._clock(), to, stamped))
        return stamped

    def hello(self) -> dict[str, Any]:
        """The first message on a line: which run this is and the newest number, so a new page starts there."""
        return {"type": "hello", "run": self.run, "last": self.last}

    def state(self) -> dict[str, Any]:
        """For a backup file: the run, the newest number, the messages young enough to go out again (with
        their age, as the clock starts new after a restart)."""
        now = self._clock()
        return {"run": self.run, "last": self.last,
                "kept": [[now - sent, to, message] for sent, to, message in self._kept
                         if now - sent <= self._max_age]}

    def restore(self, state: dict[str, Any]) -> None:
        """Goes on from a backup: same run and numbers, so a page that comes back gets just what it missed."""
        now = self._clock()
        self.run = str(state["run"])
        self.last = int(state["last"])
        self._kept.clear()
        for age, to, message in state.get("kept", []):
            self._kept.append((now - float(age), to, message))

    def since(self, run: str | None, after: int, to: str | None = None) -> list[dict[str, Any]]:
        """What a page that comes back missed: everything after its last number (after a restart: everything
        kept), not older than max_age, for its widget."""
        now = self._clock()
        return [message for sent, aimed, message in self._kept
                if (run != self.run or message["id"] > after) and now - sent <= self._max_age
                and (aimed is None or to is None or aimed == to)]
