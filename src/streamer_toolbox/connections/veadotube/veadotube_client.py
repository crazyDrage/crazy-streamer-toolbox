import asyncio
import json
import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

import websockets

CLIENT_NAME = "streamer-toolbox"  # veadotube refuses a client without a name
STATE_CHANGED = "veadotube.state"
log = logging.getLogger(__name__)


class VeadotubeClient:
    """veadotube mini's websocket (veado.tube/docs/tech/api): `ws://<address>?n=<client name>`, every message
    is `nodes: {json}`. The avatar's states are a node of type "stateEvents" (id "mini"); a message to it is
    {"event": "payload", "type": "stateEvents", "id": <node>, "payload": {...}} with the payload events list
    (→ "states": [{"id", "name"}]), peek (→ "state": <id>), set / push / pop / toggle (+ "state") and listen.

    After connecting it asks for the nodes, then the states and the state shown now, and listens. on_change gets
    {"state", "state_id", "previous"} each time the shown state becomes another one; on_state(text) reports
    "connected" or what went wrong. NOT CONFIRMED (the docs don't show it): that a listening client is told a
    change as a `peek` payload; any payload carrying a "state" is taken as the state shown now."""

    def __init__(self, address: Callable[[], str], on_change: Callable[[dict[str, Any]], Awaitable[None]],
                 on_state: Callable[[str], None] = lambda text: None,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0) -> None:
        self._address = address
        self._on_change = on_change
        self._on_state = on_state
        self._connect = connect
        self._retry_delay = retry_delay
        self._socket: Any = None
        self._node = ""
        self._states: dict[str, str] = {}  # id → name
        self._current = ""                 # id
        self._listed = asyncio.Event()

    @property
    def states(self) -> dict[str, str]:
        """The avatar's states as veadotube listed them last: id → name."""
        return dict(self._states)

    @property
    def current(self) -> str:
        """The name of the state shown now ("" before veadotube said)."""
        return self._states.get(self._current, self._current)

    async def run(self) -> None:
        """Runs until cancelled; connects again when veadotube was closed or isn't there yet."""
        delay = self._retry_delay
        while True:
            try:
                address = self._address()
                if not address:
                    raise ConnectionError("no running veadotube mini found")
                self._socket = await self._connect(url(address))
                await self._send({"event": "list"})
                delay = self._retry_delay
                async for frame in self._socket:
                    await self._handle(frame)
                raise ConnectionError("veadotube closed the line")
            except asyncio.CancelledError:
                await self._close()
                raise
            except Exception as e:
                reason = str(e) or type(e).__name__
                log.info("veadotube: %s; trying again in %.0f s", reason, delay)
                self._on_state(f"{reason}; trying again in {delay:.0f} s")
                await self._close()
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)

    async def refresh(self, timeout: float = 3.0) -> dict[str, str]:
        """Asks veadotube for its states again (the avatar may have been changed) and gives them."""
        self._listed.clear()
        await self.tell("list")
        try:
            await asyncio.wait_for(self._listed.wait(), timeout)
        except TimeoutError:
            pass
        return self.states

    async def tell(self, event: str, state_id: str = "") -> None:
        """One payload event to the avatar's node: list, peek, set, push, pop, toggle (the last four with a
        state's id). ConnectionError while veadotube isn't connected."""
        if self._socket is None or not self._node:
            raise ConnectionError("veadotube mini is not connected")
        payload = {"event": event, **({"state": state_id} if state_id else {})}
        await self._send({"event": "payload", "type": "stateEvents", "id": self._node, "payload": payload})

    async def _send(self, message: dict[str, Any]) -> None:
        await self._socket.send("nodes: " + json.dumps(message))

    async def _close(self) -> None:
        socket, self._socket, self._node = self._socket, None, ""
        if socket is not None:
            await socket.close()

    async def _handle(self, frame: Any) -> None:
        message = parse(frame)
        if message.get("event") == "list" and not self._node:
            node = next((e for e in message.get("entries") or [] if e.get("type") == "stateEvents"), None)
            if node is None:
                raise ConnectionError("this veadotube has no avatar states to switch")
            self._node = str(node.get("id") or "")
            await self.tell("list")
            await self._send({"event": "payload", "type": "stateEvents", "id": self._node,
                              "payload": {"event": "listen", "token": secrets.token_hex(4)}})
            await self.tell("peek")
            self._on_state("connected")
        elif message.get("event") == "payload" and message.get("type") == "stateEvents":
            payload = message.get("payload") or {}
            if payload.get("event") == "list":
                self._states = {str(s.get("id")): str(s.get("name") or s.get("id"))
                                for s in payload.get("states") or [] if isinstance(s, dict)}
                self._listed.set()
            elif isinstance(payload.get("state"), str) and payload.get("event") != "thumb":
                await self._shown(payload["state"])

    async def _shown(self, state_id: str) -> None:
        previous, self._current = self._current, state_id
        if previous and previous != state_id:
            try:
                await self._on_change({"state": self.current, "state_id": state_id,
                                       "previous": self._states.get(previous, previous)})
            except Exception:
                log.exception("veadotube: a state change could not be handled")


def url(address: str) -> str:
    """The websocket address with the client's name, from "127.0.0.1:2424" or a full ws:// address."""
    address = address.strip()
    if "://" not in address:
        address = "ws://" + address
    return address + ("&" if "?" in address else "?") + "n=" + quote(CLIENT_NAME)


def parse(frame: Any) -> dict[str, Any]:
    """A `nodes: {json}` frame's JSON; {} for another channel or anything unreadable."""
    text = frame.decode("utf-8", "replace") if isinstance(frame, (bytes, bytearray)) else str(frame)
    channel, colon, body = text.partition(":")
    if not colon or channel.strip() != "nodes":
        return {}
    try:
        message = json.loads(body.strip().strip("\x00"))
    except ValueError:
        return {}
    return message if isinstance(message, dict) else {}
