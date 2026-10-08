import asyncio
import json
import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

STREAMSOCKET_URL = "wss://streamsocket.kadokta.com/api/v1/streamer/custom/channel/"
EVENT = "streamsocket.event"
log = logging.getLogger(__name__)


class StreamSocketClient:
    """The "StreamSocket Events" Twitch extension's server (streamsocket.kadokta.com/documentation/api, v1, app
    source "custom"): viewers redeem events in the extension, with bits or for free, and the server tells every
    connected client. One websocket per channel; every message is {"type", "data", "request_id"?}.

    On connect the secret (from the extension's configuration page) is checked with `request_secret_check`; a
    wrong one stops it (PermissionError through on_state). The server's `request_connection_check` is answered
    with `response_connection_check`. A redemption comes as `notification_event`, or as `request_event_data`
    when the extension waits for the client's answer; that one is answered with an empty constant so the viewer
    isn't left waiting (the answer's exact meaning isn't documented beyond its fields).
    on_event(data) gets each redemption as a toolbox event's data; on_state(text) reports "listening" or what
    went wrong. The secret never appears in a message."""

    def __init__(self, channel_id: str, secret: str, on_event: Callable[[dict[str, Any]], Awaitable[None]],
                 on_state: Callable[[str], None] = lambda text: None, url: str = STREAMSOCKET_URL,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0) -> None:
        self._channel_id = channel_id
        self._secret = secret
        self._on_event = on_event
        self._on_state = on_state
        self._url = url
        self._connect = connect
        self._retry_delay = retry_delay

    async def run(self) -> None:
        """Runs until cancelled, or until the secret is refused."""
        delay = self._retry_delay
        while True:
            socket = None
            try:
                socket = await self._connect(self._url + self._channel_id)
                await self.check(socket)
                self._on_state("listening")
                delay = self._retry_delay
                async for frame in socket:
                    await self._handle(socket, frame)
                raise ConnectionError("the line closed")
            except asyncio.CancelledError:
                if socket is not None:
                    await socket.close()
                raise
            except PermissionError as e:
                self._on_state(str(e))
                if socket is not None:
                    await socket.close()
                return
            except Exception as e:
                reason = (str(e) or type(e).__name__).replace(self._secret, "<secret>")
                log.warning("StreamSocket: %s; connecting again in %.0f s", reason, delay)
                self._on_state(f"not listening ({reason}); trying again in {delay:.0f} s")
                if socket is not None:
                    await socket.close()
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    async def check(self, socket: Any, timeout: float = 15.0) -> None:
        """Asks the server whether the secret is right; PermissionError if not."""
        request = secrets.token_hex(8)
        await socket.send(json.dumps({"type": "request_secret_check", "data": {"secret": self._secret},
                                      "request_id": request}))
        while True:
            message = _message(await asyncio.wait_for(socket.recv(), timeout))
            if message.get("type") == "response_secret_check" and message.get("request_id") in (request, None):
                if not (message.get("data") or {}).get("valid"):
                    raise PermissionError("StreamSocket refused the secret: copy it again from the extension's "
                                          "configuration page")
                return
            await self._handle(socket, message)

    async def _handle(self, socket: Any, frame: Any) -> None:
        message = frame if isinstance(frame, dict) else _message(frame)
        kind, data = message.get("type"), message.get("data") or {}
        if kind == "request_connection_check":
            await socket.send(json.dumps({"type": "response_connection_check",
                                          "data": {"secret": self._secret, "active": True}}))
        elif kind in ("notification_event", "request_event_data"):
            if kind == "request_event_data":
                await socket.send(json.dumps({"type": "response_event_data", "request_id": message.get("request_id"),
                                              "data": {"data_type": "constant", "message": "",
                                                       "options": {"write_chat": False}}}))
            try:
                await self._on_event(streamsocket_event(data))
            except Exception:
                log.exception("StreamSocket: an event could not be handled")
        elif kind == "notification_error":
            log.warning("StreamSocket: %s: %s", data.get("error_name"), data.get("error_message"))


def streamsocket_event(data: dict[str, Any]) -> dict[str, Any]:
    """A redemption as the toolbox's `streamsocket.event`."""
    categories = data.get("category_ids")
    try:
        bits = int(data.get("product_bits") or 0)
    except (TypeError, ValueError):
        bits = 0
    return {"event": str(data.get("event_display_name") or data.get("event_id") or ""),
            "event_id": str(data.get("event_id") or ""), "bits": bits,
            "user": str(data.get("user_display_name") or ""), "user_id": str(data.get("user_id") or ""),
            "categories": [str(one) for one in categories] if isinstance(categories, list) else [],
            "test": bool(data.get("is_test")), "platform": "twitch"}


def _message(frame: Any) -> dict[str, Any]:
    try:
        message = json.loads(frame)
    except (ValueError, TypeError):
        return {}
    return message if isinstance(message, dict) else {}
