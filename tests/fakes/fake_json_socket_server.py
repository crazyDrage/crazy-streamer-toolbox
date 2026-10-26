import json
from collections.abc import Callable
from typing import Any

import websockets


class FakeJsonSocketServer:
    """A local websocket that talks JSON like a program with a websocket API. `answer(message, path)` says
    what comes back for each message a client sends: nothing, one message or a list of them. `greeting` is
    sent to every client right after it connects; `tell` sends a message to every connected client (an
    event). `received` keeps what clients sent (a frame that isn't JSON as its text), `paths` the address each
    client came on."""

    def __init__(self, answer: Callable[[dict[str, Any], str], Any] = lambda message, path: None,
                 greeting: list[dict[str, Any]] | None = None) -> None:
        self._answer = answer
        self._greeting = greeting or []
        self.received: list[dict[str, Any]] = []
        self.paths: list[str] = []
        self._clients: list[Any] = []
        self._server: Any = None

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self._server.sockets[0].getsockname()[1]}"

    async def __aenter__(self) -> "FakeJsonSocketServer":
        self._server = await websockets.serve(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._server.close()
        await self._server.wait_closed()

    async def tell(self, message: dict[str, Any], path: str = "") -> None:
        """Sends `message` to every connected client (only those that came on `path`, if given)."""
        for client in list(self._clients):
            if not path or client.request.path.startswith(path):
                await client.send(json.dumps(message))

    async def _handle(self, ws: Any) -> None:
        self.paths.append(ws.request.path)
        self._clients.append(ws)
        try:
            for message in self._greeting:
                await ws.send(json.dumps(message))
            async for frame in ws:
                try:
                    message = json.loads(frame)
                except ValueError:
                    self.received.append(frame)
                    continue
                self.received.append(message)
                back = self._answer(message, ws.request.path)
                for one in back if isinstance(back, list) else [back] if back is not None else []:
                    await ws.send(json.dumps(one))
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.remove(ws)
