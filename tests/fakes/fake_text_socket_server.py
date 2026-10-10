from typing import Any

import websockets


class FakeTextSocketServer:
    """A local websocket that only listens, like VNyan's receiver or Warudo's: every text a client sends is
    kept in `received`, the address each came on in `paths`; `connections` counts connects."""

    def __init__(self, path: str = "/") -> None:
        self._path = path
        self.connections = 0
        self.paths: list[str] = []
        self.received: list[str] = []
        self._server: Any = None

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self._server.sockets[0].getsockname()[1]}{self._path}"

    async def __aenter__(self) -> "FakeTextSocketServer":
        self._server = await websockets.serve(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._server.close()
        await self._server.wait_closed()

    async def _handle(self, ws: Any) -> None:
        self.connections += 1
        self.paths.append(ws.request.path)
        try:
            async for frame in ws:
                self.received.append(frame)
        except websockets.ConnectionClosed:
            pass
