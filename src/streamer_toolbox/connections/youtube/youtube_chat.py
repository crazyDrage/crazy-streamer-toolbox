import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from streamer_toolbox.connections.youtube.youtube_api import YouTubeApi
from streamer_toolbox.connections.youtube.youtube_api_error import YouTubeApiError
from streamer_toolbox.connections.youtube.youtube_events import ENDED, OFFLINE, ONLINE, PLATFORM, youtube_events

log = logging.getLogger(__name__)
GONE = ("liveChatEnded", "liveChatNotFound", "liveChatDisabled")
QUOTA = ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded")
NOT_ENABLED = "liveStreamingNotEnabled"  # the channel never switched live streaming on: no login problem


class YouTubeChat:
    """Follows his live chat. While he isn't live it looks for a live stream every `look` seconds (1 quota
    point each). Once one is found: `youtube.online`, then the chat is asked again and again, not faster than
    YouTube allows (its pollingIntervalMillis) and not faster than `every` seconds; each message becomes its
    events (youtube_events). The first answer is the chat's history: not news. When the chat ends:
    `youtube.offline`, and looking starts again.

    Asking costs quota (a chat answer about 5 points; not confirmed by Google's table), so `every` decides how
    many hours of stream a day's 10 000 points last. A used-up quota is told through on_state and waited out.
    on_event(kind, data) gets each event; on_state(text) reports "waiting for a stream", "listening" or what
    went wrong. The found chat is in `chat` (None while not live), for the send box."""

    def __init__(self, api: YouTubeApi, on_event: Callable[[str, dict[str, Any]], Awaitable[None]],
                 on_state: Callable[[str], None] = lambda text: None, every: float = 10.0, look: float = 60.0,
                 quota_wait: float = 600.0) -> None:
        self._api = api
        self._on_event = on_event
        self._on_state = on_state
        self._every = every
        self._look = look
        self._quota_wait = quota_wait
        self.chat: dict[str, str] | None = None

    async def run(self) -> None:
        """Runs until cancelled, or until the login is refused (PermissionError goes to the caller)."""
        while True:
            try:
                self.chat = await self._api.live_chat()
                if self.chat is None:
                    self._on_state("waiting for a stream")
                    await asyncio.sleep(self._look)
                    continue
                await self._tell(ONLINE, {"title": self.chat["title"], "platform": PLATFORM})
                await self._follow(self.chat["chat"])
                await self._tell(OFFLINE, {"title": self.chat["title"], "platform": PLATFORM})
                self.chat = None
                await asyncio.sleep(self._look)  # YouTube may list the ended stream as live a moment longer
            except YouTubeApiError as e:
                self.chat = None
                if e.reason in QUOTA:
                    self._on_state("today's YouTube quota is used up (it starts again at midnight Pacific time); "
                                   "ask less often under \"Ask every\"")
                    await asyncio.sleep(self._quota_wait)
                elif e.reason == NOT_ENABLED:
                    self._on_state("not listening (live streaming isn't switched on for this YouTube channel: "
                                   "YouTube Studio → Go live; YouTube takes up to 24 hours to enable it)")
                    await asyncio.sleep(self._quota_wait)
                elif e.status in (401, 403):
                    raise PermissionError(f"YouTube refused the login ({e}): press Connect to log in again") from e
                else:
                    await self._again(str(e))
            except httpx.HTTPError as e:
                self.chat = None
                await self._again(f"can't reach YouTube: {type(e).__name__}")

    async def _follow(self, chat: str) -> None:
        """Asks the chat until it ends."""
        page, first = "", True
        while True:
            try:
                answer = await self._api.chat_messages(chat, page)
            except YouTubeApiError as e:
                if e.reason in GONE or e.status == 404:
                    return
                raise
            self._on_state("listening")
            ended = False
            for message in answer.get("items") or []:
                if not isinstance(message, dict):
                    continue
                ended = ended or (message.get("snippet") or {}).get("type") == ENDED
                for kind, data in ([] if first else youtube_events(message)):
                    await self._tell(kind, data)
            if ended or answer.get("offlineAt"):
                return
            page, first = str(answer.get("nextPageToken") or page), False
            try:
                allowed = float(answer.get("pollingIntervalMillis", 0)) / 1000
            except (TypeError, ValueError):
                allowed = 0.0
            await asyncio.sleep(max(allowed, self._every))

    async def _again(self, reason: str) -> None:
        log.warning("YouTube: %s; trying again in %.0f s", reason, self._look)
        self._on_state(f"not listening ({reason}); trying again")
        await asyncio.sleep(self._look)

    async def _tell(self, kind: str, data: dict[str, Any]) -> None:
        try:
            await self._on_event(kind, data)
        except Exception:
            log.exception("YouTube: an event could not be handled")
