import asyncio
import json
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

EVENTSUB_URL = "wss://eventsub.wss.twitch.tv/ws"
log = logging.getLogger(__name__)


class EventSubClient:
    """Twitch EventSub over WebSocket (dev.twitch.tv/docs/eventsub/handling-websocket-events).

    Twitch says hello with a session id; on_welcome(session_id) must then create the subscriptions (within 10 s).
    Events arrive as on_event(type, event). Keepalives show the line is alive; if they stop, or the socket
    closes, it connects again and subscribes again. A "session_reconnect" moves to the new address Twitch
    gives (the subscriptions move along; the old socket closes after the new one said hello).
    on_state(text) reports "listening" or what went wrong, for the Twitch tab.
    """

    def __init__(self, on_welcome: Callable[[str], Awaitable[None]],
                 on_event: Callable[[str, dict[str, Any]], Awaitable[None]],
                 on_state: Callable[[str], None] = lambda text: None, url: str = EVENTSUB_URL,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0) -> None:
        self._on_welcome = on_welcome
        self._on_event = on_event
        self._on_state = on_state
        self._url = url
        self._connect = connect
        self._retry_delay = retry_delay
        self._seen: deque[str] = deque(maxlen=200)  # Twitch may send a message twice

    async def run(self) -> None:
        """Runs until cancelled."""
        delay = self._retry_delay
        while True:
            ws = None
            try:
                ws = await self._connect(self._url)
                session_id, keepalive = await self._welcome(ws)
                await self._on_welcome(session_id)
                self._on_state("listening")
                delay = self._retry_delay
                while True:
                    next_url = await self._listen(ws, keepalive)
                    new_ws = await self._connect(next_url)
                    _, keepalive = await self._welcome(new_ws)
                    await ws.close()
                    ws = new_ws
            except asyncio.CancelledError:
                if ws is not None:
                    await ws.close()
                raise
            except Exception as e:
                log.warning("EventSub: %s; connecting again in %.0f s", e, delay)
                self._on_state(f"not listening ({e}); trying again in {delay:.0f} s")
                if ws is not None:
                    await ws.close()
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    async def _welcome(self, ws: Any) -> tuple[str, float]:
        message = json.loads(await asyncio.wait_for(ws.recv(), 15))
        if message["metadata"]["message_type"] != "session_welcome":
            raise ConnectionError(f"expected a welcome, got {message['metadata']['message_type']}")
        session = message["payload"]["session"]
        return session["id"], float(session.get("keepalive_timeout_seconds") or 10)

    async def _listen(self, ws: Any, keepalive: float) -> str:
        """Handles messages until Twitch asks to reconnect; returns the new address."""
        while True:
            raw = await asyncio.wait_for(ws.recv(), keepalive + 5)  # no keepalive in time: TimeoutError
            message = json.loads(raw)
            meta, payload = message["metadata"], message.get("payload", {})
            kind = meta["message_type"]
            if kind == "session_reconnect":
                return payload["session"]["reconnect_url"]
            if kind == "notification" and meta.get("message_id") not in self._seen:
                self._seen.append(meta.get("message_id"))
                await self._on_event(payload["subscription"]["type"], payload["event"])
            elif kind == "revocation":
                self._on_state(f"Twitch ended the subscription {payload['subscription']['type']} "
                               f"({payload['subscription'].get('status')})")
