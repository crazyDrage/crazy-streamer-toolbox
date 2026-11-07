import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.followers.seen_followers import SeenFollowers

log = logging.getLogger(__name__)
FASTEST = 10.0  # seconds: never asks more often than this


class FollowerCheck:
    """A failsafe for follows a platform's live event missed (his ask of 2026-11-05: "sometimes twitch doesn't
    see new followers ... check the last followers every minute"). Every `every()` seconds it asks the platform
    for its newest followers (`newest()`: dicts with the follow event's fields, newest first, each with a
    "user_id") and sends a follow event for each one the SeenFollowers list doesn't have yet, oldest first.
    The live event checks the same list, so a follow comes once, whichever sees it first. The very first check
    (an empty list) only fills the list. every() = 0 switches it off; a failed ask is tried again next time."""

    def __init__(self, newest: Callable[[], Awaitable[list[dict[str, Any]]]],
                 publish: Callable[[dict[str, Any]], None], seen: SeenFollowers,
                 every: Callable[[], float]) -> None:
        self._newest = newest
        self._publish = publish
        self._seen = seen
        self._every = every

    async def run(self) -> None:
        while True:
            seconds = self._every()
            if seconds <= 0:
                return
            try:
                await self.check()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.info("follower check: %s", e)
            await asyncio.sleep(max(seconds, FASTEST))

    async def check(self) -> list[dict[str, Any]]:
        """One ask; the follows it sent."""
        followers = await self._newest()
        if self._seen.empty:
            self._seen.fill(reversed([str(f.get("user_id", "")) for f in followers]))
            return []
        sent = []
        for follower in reversed(followers):
            if str(follower.get("user_id", "")).strip() and self._seen.fresh(follower["user_id"]):
                self._publish(follower)
                sent.append(follower)
        return sent
