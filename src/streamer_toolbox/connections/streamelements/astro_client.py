import asyncio
import json
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

from streamer_toolbox.connections.streamelements.astro_events import TOPIC

ASTRO_URL = "wss://astro.streamelements.com"
log = logging.getLogger(__name__)


class AstroClient:
    """StreamElements' Astro websocket (docs.streamelements.com/websockets), listening only: connects, subscribes
    to the channel's activities with the account's JWT, and hands every message to on_message. If the line
    drops, or StreamElements asks to reconnect, it connects and subscribes again (their pings are answered by
    the websockets library). A refused subscription (a wrong or expired token) is a PermissionError: it stops
    trying, since asking again won't help. on_state(text) reports "listening" or what went wrong."""

    def __init__(self, token: str, room: str, on_message: Callable[[dict[str, Any]], Awaitable[None]],
                 on_state: Callable[[str], None] = lambda text: None, url: str = ASTRO_URL,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0) -> None:
        self._token = token
        self._room = room
        self._on_message = on_message
        self._on_state = on_state
        self._url = url
        self._connect = connect
        self._retry_delay = retry_delay
        self._seen: deque[str] = deque(maxlen=200)  # after a reconnect a message may come twice

    async def run(self) -> None:
        """Runs until cancelled, or until the token is refused."""
        delay = self._retry_delay
        while True:
            socket = None
            try:
                socket = await self._connect(self._url)
                await self.subscribe(socket)
                self._on_state("listening")
                delay = self._retry_delay
                await self._listen(socket)
                await socket.close()  # asked to reconnect: the old line is not left open
            except asyncio.CancelledError:
                if socket is not None:
                    await socket.close()
                raise
            except PermissionError as e:
                self._on_state(str(e))
                if socket is not None:
                    await socket.close()
                return
            except Exception as e:
                log.warning("StreamElements: %s; connecting again in %.0f s", e, delay)
                self._on_state(f"not listening ({e}); trying again in {delay:.0f} s")
                if socket is not None:
                    await socket.close()
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    async def subscribe(self, socket: Any, timeout: float = 15.0) -> None:
        """Asks for the activities and waits for the answer; PermissionError if StreamElements says no."""
        data = {"topic": TOPIC, "token": self._token, "token_type": "jwt"}
        if self._room:
            data["room"] = self._room
        await socket.send(json.dumps({"type": "subscribe", "nonce": "toolbox", "data": data}))
        while True:
            message = json.loads(await asyncio.wait_for(socket.recv(), timeout))
            if message.get("type") != "response" or message.get("nonce") != "toolbox":
                continue  # their welcome
            answer = message.get("data") or {}
            if message.get("error") or "success" not in str(answer.get("message", "")).casefold():
                reason = message.get("error") or answer.get("message") or answer
                raise PermissionError(f"StreamElements refused the token: {reason}")
            return

    async def _listen(self, socket: Any) -> None:
        """Handles messages until the line closes or StreamElements asks to reconnect."""
        while True:
            message = json.loads(await socket.recv())
            if message.get("type") == "reconnect":
                return
            if message.get("type") != "message" or message.get("id") in self._seen:
                continue
            self._seen.append(message.get("id"))
            try:
                await self._on_message(message)
            except Exception:
                log.exception("StreamElements: a message could not be handled")
