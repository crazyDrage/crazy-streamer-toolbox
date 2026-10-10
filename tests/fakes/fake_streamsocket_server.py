import asyncio
import json
from typing import Any

import websockets


class FakeStreamSocketServer:
    """A local websocket that talks like StreamSocket Events' server: answers `request_secret_check` (valid
    only for `secret`), and sends what the test gives it with send(). Everything clients send is kept in
    `received`; `paths` keeps the address each came on; `connections` counts connects."""

    def __init__(self, secret: str = "the-secret") -> None:
        self.secret = secret
        self.connections = 0
        self.paths: list[str] = []
        self.received: list[dict[str, Any]] = []
        self.checked = asyncio.Event()
        self._clients: list[Any] = []
        self._server: Any = None

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self._server.sockets[0].getsockname()[1]}/api/v1/streamer/custom/channel/"

    async def __aenter__(self) -> "FakeStreamSocketServer":
        self._server = await websockets.serve(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._server.close()
        await self._server.wait_closed()

    async def send(self, kind: str, data: dict[str, Any] | None = None, request_id: str | None = None) -> None:
        message = {"type": kind, **({"data": data} if data is not None else {}),
                   **({"request_id": request_id} if request_id else {})}
        await self._clients[-1].send(json.dumps(message))

    async def _handle(self, ws: Any) -> None:
        self.connections += 1
        self.paths.append(ws.request.path)
        self._clients.append(ws)
        try:
            async for frame in ws:
                message = json.loads(frame)
                self.received.append(message)
                if message["type"] == "request_secret_check":
                    await ws.send(json.dumps({"type": "response_secret_check", "request_id": message["request_id"],
                                              "data": {"valid": message["data"]["secret"] == self.secret}}))
                    self.checked.set()
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.remove(ws)
