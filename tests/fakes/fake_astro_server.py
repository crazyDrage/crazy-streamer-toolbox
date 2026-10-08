import asyncio
import json
from typing import Any

import websockets


class FakeAstroServer:
    """A local websocket that talks like StreamElements' Astro gateway: a welcome on connect, an answer to each
    subscribe (refused when `accept` is False), then whatever the test sends with activity() / ask_reconnect().
    `subscriptions` keeps what clients asked for."""

    def __init__(self, accept: bool = True) -> None:
        self.accept = accept
        self.subscriptions: list[dict[str, Any]] = []
        self.subscribed = asyncio.Event()
        self._clients: list[Any] = []
        self._server: Any = None
        self._sent = 0

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self._server.sockets[0].getsockname()[1]}"

    async def __aenter__(self) -> "FakeAstroServer":
        self._server = await websockets.serve(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._server.close()
        await self._server.wait_closed()

    async def activity(self, kind: str, data: dict[str, Any], mock: bool = False, message_id: str = "") -> None:
        self._sent += 1
        await self._send({"id": message_id or f"m{self._sent}", "type": "message", "topic": "channel.activities",
                          "room": "room1", "data": {"channel": "room1", "provider": "twitch", "type": kind,
                                                    "isMock": mock, "data": data}})

    async def ask_reconnect(self) -> None:
        await self._send({"id": "rc", "type": "reconnect", "data": {"reconnect_token": "again"}})

    async def _send(self, message: dict[str, Any]) -> None:
        await self._clients[-1].send(json.dumps(message))

    async def _handle(self, ws: Any) -> None:
        self._clients.append(ws)
        await ws.send(json.dumps({"id": "w", "type": "welcome", "data": {"client_id": "c", "message": "hello"}}))
        try:
            async for raw in ws:
                asked = json.loads(raw)
                self.subscriptions.append(asked["data"])
                text = "successfully subscribed to topic" if self.accept else "invalid token"
                await ws.send(json.dumps({"id": "r", "type": "response", "nonce": asked["nonce"],
                                          "data": {"message": text, "topic": asked["data"]["topic"]}}))
                self.subscribed.set()
        finally:
            self._clients.remove(ws)
