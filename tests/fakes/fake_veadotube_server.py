import json
from typing import Any

import websockets

NODE = {"type": "stateEvents", "id": "mini", "name": "avatar state"}


class FakeVeadotubeServer:
    """A local websocket that talks like veadotube mini (veado.tube/docs/tech/api/nodes): refuses a client
    without a name (?n=), lists its nodes, and for the avatar's stateEvents node answers list and peek and
    keeps a stack of states for set / push / pop / toggle. A client that sent `listen` is told the shown state
    as a peek payload whenever it changes (the docs don't show that message; this is the client's assumption).
    `states` is id → name; `stack` the stack (the last one shows); `paths` the address each client came on."""

    def __init__(self, states: dict[str, str] | None = None) -> None:
        self.states = states if states is not None else {"1": "idle", "2": "happy", "3": "angry"}
        self.stack = [next(iter(self.states))]
        self.paths: list[str] = []
        self.received: list[dict[str, Any]] = []
        self._listening: list[Any] = []
        self._server: Any = None

    @property
    def address(self) -> str:
        return f"127.0.0.1:{self._server.sockets[0].getsockname()[1]}"

    @property
    def shown(self) -> str:
        return self.states[self.stack[-1]]

    async def __aenter__(self) -> "FakeVeadotubeServer":
        self._server = await websockets.serve(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._server.close()
        await self._server.wait_closed()

    async def _handle(self, ws: Any) -> None:
        self.paths.append(ws.request.path)
        if "n=" not in ws.request.path:
            await ws.close()
            return
        try:
            async for frame in ws:
                channel, _, body = frame.partition(":")
                message = json.loads(body)
                self.received.append(message)
                if channel != "nodes":
                    continue
                if message["event"] == "list":
                    await self._say(ws, {"event": "list", "entries": [
                        {"type": "boolean", "id": "mini", "name": "push-to-talk"}, NODE]})
                elif message["event"] == "payload":
                    await self._payload(ws, message["payload"])
        except websockets.ConnectionClosed:
            pass
        finally:
            if ws in self._listening:
                self._listening.remove(ws)

    async def _payload(self, ws: Any, payload: dict[str, Any]) -> None:
        event, state = payload["event"], payload.get("state")
        before = self.stack[-1]
        if event == "list":
            await self._node(ws, {"event": "list", "states": [
                {"id": i, "name": n, "thumbHash": "x"} for i, n in self.states.items()]})
        elif event == "peek":
            await self._node(ws, {"event": "peek", "state": self.stack[-1]})
        elif event == "listen":
            self._listening.append(ws)
        elif event == "set":
            self.stack = [state]
        elif event == "push" or (event == "toggle" and state not in self.stack):
            self.stack.append(state)
        elif event in ("pop", "toggle") and state in self.stack and len(self.stack) > 1:
            self.stack.reverse()
            self.stack.remove(state)
            self.stack.reverse()
        if self.stack[-1] != before:
            for listener in self._listening:
                await self._node(listener, {"event": "peek", "state": self.stack[-1]})

    async def _node(self, ws: Any, payload: dict[str, Any]) -> None:
        await self._say(ws, {"event": "payload", **NODE, "payload": payload})

    @staticmethod
    async def _say(ws: Any, message: dict[str, Any]) -> None:
        await ws.send("nodes: " + json.dumps(message))
