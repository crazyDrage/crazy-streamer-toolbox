import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from typing import Any

import websockets

from streamer_toolbox.connections.vtube_studio.vts_api_error import VtsApiError

API = {"apiName": "VTubeStudioPublicAPI", "apiVersion": "1.0"}
log = logging.getLogger(__name__)


class VtsClient:
    """The VTube Studio Public API over one websocket (github.com/DenchiSoft/VTubeStudio).

    Async: every request waits for the answer with the same requestID. Events VTS sends by itself (after an
    EventSubscriptionRequest, e.g. "ModelLoadedEvent") go to on_event(type, data).
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self.on_event: Callable[[str, dict[str, Any]], None] | None = None
        self._ws: Any = None
        self._reader: asyncio.Task | None = None
        self._waiting: dict[str, asyncio.Future] = {}

    @property
    def is_open(self) -> bool:
        return self._ws is not None and self._reader is not None and not self._reader.done()

    async def connect(self) -> None:
        self._ws = await websockets.connect(self.url, max_size=None)
        self._reader = asyncio.create_task(self._read_loop())

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
        if self._reader is not None:
            await asyncio.gather(self._reader, return_exceptions=True)
        self._ws = self._reader = None

    async def request(self, message_type: str, data: dict[str, Any] | None = None,
                      timeout: float = 10) -> dict[str, Any]:
        if not self.is_open:
            raise ConnectionError(f"not connected to VTube Studio at {self.url}")
        request_id = uuid.uuid4().hex
        answer = asyncio.get_running_loop().create_future()
        self._waiting[request_id] = answer
        try:
            await self._ws.send(json.dumps({**API, "requestID": request_id, "messageType": message_type,
                                            "data": data or {}}))
            message = await asyncio.wait_for(answer, timeout)
        finally:
            self._waiting.pop(request_id, None)
        if message["messageType"] == "APIError":
            raise VtsApiError(message_type, message["data"].get("errorID", -1), message["data"].get("message", ""))
        return message.get("data", {})

    async def _read_loop(self) -> None:
        try:
            async for raw in self._ws:
                message = json.loads(raw)
                answer = self._waiting.get(message.get("requestID", ""))
                if answer is not None and not answer.done():
                    answer.set_result(message)
                elif message.get("messageType", "").endswith("Event") and self.on_event is not None:
                    try:
                        self.on_event(message["messageType"], message.get("data", {}))
                    except Exception:
                        log.exception("VTS event %s", message["messageType"])
        finally:
            for answer in self._waiting.values():
                if not answer.done():
                    answer.set_exception(ConnectionError("VTube Studio closed the connection"))
