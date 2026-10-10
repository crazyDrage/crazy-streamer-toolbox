import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime

from streamer_toolbox.core.events.role_book import RoleBook
from streamer_toolbox.core.events.role_loading import CHAT, EVERY, RoleLoading

log = logging.getLogger(__name__)
Read = Callable[[], Awaitable[tuple[dict[str, str], dict[str, int]]]]  # → (user id → role, the counts)


class RoleLoader:
    """Loads a platform's role lists into the RoleBook when the setting says so (RoleLoading): once after
    the start, or again every so many minutes. `run` looks every `check` seconds whether a load is due; one
    that fails (Twitch not connected yet, a right missing) is tried again after `retry` seconds.

    `status` says in one line what happened last, for Settings → Viewer roles; `load` loads now (its button)."""

    def __init__(self, book: RoleBook, setting: RoleLoading, read: Read, platform: str = "twitch",
                 check: float = 15.0, retry: float = 60.0, now: Callable[[], float] = time.monotonic,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self._book = book
        self._setting = setting
        self._read = read
        self._platform = platform
        self._check = check
        self._retry = retry
        self._now = now
        self._clock = clock
        self._loaded_at: float | None = None
        self._tried_at: float | None = None
        self.status = "Not loaded yet."

    async def run(self) -> None:
        """Runs until cancelled."""
        while True:
            if self.due():
                await self.load()
            await asyncio.sleep(self._check)

    def due(self) -> bool:
        mode, now = self._setting.mode, self._now()
        if mode == CHAT or (self._tried_at is not None and now - self._tried_at < self._retry):
            return False
        if self._loaded_at is None:
            return True
        return mode == EVERY and now - self._loaded_at >= self._setting.minutes * 60

    async def load(self) -> bool:
        self._tried_at = self._now()
        try:
            roles, counts = await self._read()
        except Exception as e:  # said on the settings page; the triggers go on with what chat told
            self.status = f"Not loaded: {e}"
            log.info("viewer roles not loaded: %s", e)
            return False
        self._book.load(self._platform, roles)
        self._loaded_at = self._now()
        self.status = (f"Loaded at {self._clock():%H:%M}: {counts.get('mod', 0)} mods, {counts.get('vip', 0)} VIPs, "
                       f"{counts.get('sub', 0)} subs ({counts.get('requests', 0)} requests).")
        return True
