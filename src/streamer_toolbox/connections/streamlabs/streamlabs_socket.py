import asyncio
import json
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

STREAMLABS_URL = "wss://sockets.streamlabs.com/socket.io/?EIO=3&transport=websocket&token="
log = logging.getLogger(__name__)


class StreamlabsSocket:
    """Streamlabs' Socket API (dev.streamlabs.com/docs/socket-api), listening only. Their server speaks the old
    Socket.IO 2 / Engine.IO 3 protocol, which today's python-socketio can't; the part that's needed is small, so
    it's done here on a plain websocket: `0{...}` = open (with the ping interval), `40` = connected, `44...` = an
    error (a wrong token: PermissionError, it stops trying), `42["event", {...}]` = an event, and every ping
    interval we send `2` and they answer `3`. No answer in time, or a closed line: connect again.
    on_event(payload) gets each event; on_state(text) reports "listening" or what went wrong."""

    def __init__(self, token: str, on_event: Callable[[dict[str, Any]], Awaitable[None]],
                 on_state: Callable[[str], None] = lambda text: None, url: str = STREAMLABS_URL,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0) -> None:
        self._token = token
        self._on_event = on_event
        self._on_state = on_state
        self._url = url
        self._connect = connect
        self._retry_delay = retry_delay
        self._seen: deque[str] = deque(maxlen=200)  # after a reconnect an event may come twice

    async def run(self) -> None:
        """Runs until cancelled, or until the token is refused."""
        delay = self._retry_delay
        while True:
            socket = None
            try:
                socket = await self._connect(self._url + self._token)
                interval, patience = await self.open(socket)
                self._on_state("listening")
                delay = self._retry_delay
                await self._listen(socket, interval, patience)
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
                reason = str(e).replace(self._token, "<token>") or type(e).__name__
                log.warning("Streamlabs: %s; connecting again in %.0f s", reason, delay)
                self._on_state(f"not listening ({reason}); trying again in {delay:.0f} s")
                if socket is not None:
                    await socket.close()
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    async def open(self, socket: Any, timeout: float = 15.0) -> tuple[float, float]:
        """Waits until Streamlabs says the line is open and we're connected; gives (seconds between our pings,
        seconds to wait for an answer). PermissionError if it refuses."""
        interval, patience = 25.0, 20.0
        while True:
            frame = await asyncio.wait_for(socket.recv(), timeout)
            if frame.startswith("0"):
                opened = json.loads(frame[1:])
                interval = float(opened.get("pingInterval", 25000)) / 1000
                patience = float(opened.get("pingTimeout", 20000)) / 1000
            elif frame.startswith("44"):
                raise PermissionError(f"Streamlabs refused the token: {frame[2:].strip() or 'no reason given'}")
            elif frame.startswith("40"):
                return interval, patience

    async def _listen(self, socket: Any, interval: float, patience: float) -> None:
        """Handles events and keeps the line alive until it closes or goes quiet."""
        loop = asyncio.get_running_loop()
        next_ping = loop.time() + interval
        waiting_since: float | None = None  # when our last ping went out, None once it was answered
        while True:
            now = loop.time()
            if waiting_since is not None and now - waiting_since > patience:
                raise ConnectionError("no answer to our ping")
            if now >= next_ping:
                await socket.send("2")
                waiting_since = waiting_since if waiting_since is not None else now
                next_ping = now + interval
            try:
                frame = await asyncio.wait_for(socket.recv(), max(min(next_ping - loop.time(), patience), 0.05))
            except asyncio.TimeoutError:
                continue
            if frame == "3":
                waiting_since = None
            elif frame.startswith("44"):
                raise PermissionError(f"Streamlabs refused the token: {frame[2:].strip() or 'no reason given'}")
            elif frame.startswith("42"):
                await self._event(frame[2:])

    async def _event(self, text: str) -> None:
        try:
            name, payload = json.loads(text)[:2]
        except (ValueError, TypeError):
            return
        if name != "event" or not isinstance(payload, dict):
            return
        event_id = payload.get("event_id")
        if event_id:
            if event_id in self._seen:
                return
            self._seen.append(event_id)
        try:
            await self._on_event(payload)
        except Exception:
            log.exception("Streamlabs: an event could not be handled")
