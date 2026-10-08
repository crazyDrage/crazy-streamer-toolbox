import asyncio
import json
from typing import Any

import websockets


class FakeEventSubServer:
    """A local websocket that talks like Twitch's EventSub: a welcome on connect, then whatever the test sends
    with notify() / reconnect_to(). `sessions` counts welcomes."""

    def __init__(self, keepalive: int = 10) -> None:
        self.keepalive = keepalive
        self.sessions = 0
        self.connected = asyncio.Event()
        self._clients: list[Any] = []
        self._server: Any = None

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self._server.sockets[0].getsockname()[1]}"

    async def __aenter__(self) -> "FakeEventSubServer":
        self._server = await websockets.serve(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._server.close()
        await self._server.wait_closed()

    async def notify(self, kind: str, event: dict[str, Any], message_id: str = "m1") -> None:
        await self._send({"metadata": {"message_id": message_id, "message_type": "notification"},
                          "payload": {"subscription": {"type": kind}, "event": event}})

    async def reconnect_to(self, url: str) -> None:
        await self._send({"metadata": {"message_id": "rc", "message_type": "session_reconnect"},
                          "payload": {"session": {"id": "old", "reconnect_url": url}}})

    async def _send(self, message: dict[str, Any]) -> None:
        await self._clients[-1].send(json.dumps(message))

    async def _handle(self, ws: Any) -> None:
        self.sessions += 1
        self._clients.append(ws)
        await ws.send(json.dumps({"metadata": {"message_id": f"w{self.sessions}", "message_type": "session_welcome"},
                                  "payload": {"session": {"id": f"session-{self.sessions}",
                                                          "keepalive_timeout_seconds": self.keepalive}}}))
        self.connected.set()
        try:
            await ws.wait_closed()
        finally:
            self._clients.remove(ws)
