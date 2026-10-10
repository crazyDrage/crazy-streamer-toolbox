import time
from collections.abc import Callable
from typing import Any

from streamer_toolbox.core.flows.flow import Flow


class FlowCooldowns:
    """A flow's cooldowns for its triggers (its button and other flows aren't held back): `cooldown` seconds for
    everyone after a start, `user_cooldown` seconds for the same viewer (the event's user_login)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._last: dict[str, float] = {}             # flow → last start
        self._last_user: dict[tuple[str, str], float] = {}  # (flow, viewer) → their last start

    def wait_left(self, flow: Flow, data: dict[str, Any]) -> float:
        """Seconds until the flow may start again for this event; 0 = it may now."""
        now, user = self._clock(), str(data.get("user_login", "")).casefold()
        left = 0.0
        if flow.cooldown > 0 and flow.name in self._last:
            left = self._last[flow.name] + flow.cooldown - now
        if flow.user_cooldown > 0 and user and (flow.name, user) in self._last_user:
            left = max(left, self._last_user[(flow.name, user)] + flow.user_cooldown - now)
        return max(left, 0.0)

    def started(self, flow: Flow, data: dict[str, Any]) -> None:
        now, user = self._clock(), str(data.get("user_login", "")).casefold()
        self._last[flow.name] = now
        if user:
            self._last_user[(flow.name, user)] = now
