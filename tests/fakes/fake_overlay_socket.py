import asyncio
import json
from typing import Any

from fastapi import WebSocketDisconnect


class FakeOverlaySocket:
    """An overlay page's socket for api/overlay_line: what the toolbox sends lands in `sent`; `say` is what the
    page sends back; `leave` is the page closing."""

    def __init__(self, query: dict[str, str] | None = None) -> None:
        self.query_params = query or {}
        self.sent: list[dict[str, Any]] = []
        self.closed = False
        self._said: asyncio.Queue = asyncio.Queue()

    async def send_json(self, message: dict[str, Any]) -> None:
        self.sent.append(message)

    async def receive_text(self) -> str:
        said = await self._said.get()
        if said is None:
            raise WebSocketDisconnect()
        return said

    async def close(self) -> None:
        self.closed = True

    def say(self, message: dict[str, Any]) -> None:
        self._said.put_nowait(json.dumps(message))

    def leave(self) -> None:
        self._said.put_nowait(None)
