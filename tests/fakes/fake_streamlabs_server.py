import asyncio
import json
from typing import Any

import websockets


class FakeStreamlabsServer:
    """A local websocket that talks like Streamlabs' socket (Engine.IO 3): `0{...}` and `40` on connect (`44` when
    `accept` is False), answers a `2` with `3` (unless `answer_pings` is off), and sends what the test gives it
    with event(). `connections` counts connects, `tokens` keeps the token each came with, `pings` counts pings."""

    def __init__(self, accept: bool = True, ping_interval: float = 0.05, ping_timeout: float = 0.2) -> None:
        self.accept = accept
        self.answer_pings = True
        self.ping_interval, self.ping_timeout = ping_interval, ping_timeout
        self.connections = 0
        self.pings = 0
        self.tokens: list[str] = []
        self.connected = asyncio.Event()
        self._clients: list[Any] = []
        self._server: Any = None

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self._server.sockets[0].getsockname()[1]}/socket.io/?EIO=3&transport=websocket&token="

    async def __aenter__(self) -> "FakeStreamlabsServer":
        self._server = await websockets.serve(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._server.close()
        await self._server.wait_closed()

    async def event(self, payload: dict[str, Any], name: str = "event") -> None:
        await self._clients[-1].send("42" + json.dumps([name, payload]))

    async def _handle(self, ws: Any) -> None:
        self.connections += 1
        self.tokens.append(ws.request.path.rsplit("token=", 1)[-1])
        self._clients.append(ws)
        await ws.send("0" + json.dumps({"sid": "s", "upgrades": [], "pingInterval": self.ping_interval * 1000,
                                        "pingTimeout": self.ping_timeout * 1000}))
        await ws.send("40" if self.accept else '44"Invalid token"')
        self.connected.set()
        try:
            async for frame in ws:
                if frame == "2":
                    self.pings += 1
                    if self.answer_pings:
                        await ws.send("3")
        except websockets.ConnectionClosed:  # the client left between its ping and our answer
            pass
        finally:
            self._clients.remove(ws)
