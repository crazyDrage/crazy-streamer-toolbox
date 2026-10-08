import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from streamer_toolbox.connections.rumble.rumble_news import RumbleNews

HOST = "rumble.com"
log = logging.getLogger(__name__)


class RumbleFeed:
    """Asks Rumble's Live Stream API again and again and hands on what is new (RumbleNews). The API is one
    address with the account's key in it (rumble.com → account → Live Stream API); there is nothing to listen
    to, so asking is the only way. A refused key (401 / 403 / 404) stops it: PermissionError-like, told through
    on_state. Anything else (no internet, a server error) is tried again.
    on_event(kind, data) gets each event; on_state(text) reports "listening" or what went wrong. The address
    never appears in a message: it is the key."""

    def __init__(self, address: str, on_event: Callable[[str, dict[str, Any]], Awaitable[None]],
                 on_state: Callable[[str], None] = lambda text: None, every: float = 5.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._address = address
        self._on_event = on_event
        self._on_state = on_state
        self._every = every
        self._transport = transport
        self._news = RumbleNews()

    async def ask(self) -> dict[str, Any]:
        """One answer. PermissionError if Rumble refuses the address, ConnectionError for anything else."""
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=10) as client:
                answer = await client.get(self._address)
        except httpx.HTTPError as e:
            raise ConnectionError(type(e).__name__) from None  # its text would name the address
        if answer.status_code in (401, 403, 404):
            raise PermissionError(f"Rumble refused the address ({answer.status_code}): is it the whole Live "
                                  "Stream API address, with the key?")
        if answer.status_code != 200:
            raise ConnectionError(f"Rumble answered {answer.status_code}")
        try:
            data = answer.json()
        except ValueError:
            raise ConnectionError("Rumble's answer wasn't JSON") from None
        if not isinstance(data, dict):
            raise ConnectionError("Rumble's answer wasn't an object")
        return data

    async def run(self) -> None:
        """Runs until cancelled, or until the address is refused."""
        while True:
            try:
                answer = await self.ask()
            except PermissionError as e:
                self._on_state(str(e))
                return
            except ConnectionError as e:
                log.warning("Rumble: %s; asking again in %.0f s", e, self._every * 4)
                self._on_state(f"not listening ({e}); trying again")
                await asyncio.sleep(self._every * 4)
                continue
            self._on_state("listening")
            for kind, data in self._news.news(answer):
                try:
                    await self._on_event(kind, data)
                except Exception:
                    log.exception("Rumble: an event could not be handled")
            await asyncio.sleep(self._every)
