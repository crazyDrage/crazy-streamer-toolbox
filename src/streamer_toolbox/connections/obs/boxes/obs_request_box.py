from collections.abc import Awaitable, Callable
from typing import Any

import simpleobsws

from streamer_toolbox.connections.obs.obs_protocol import ObsProtocol
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.core.interfaces.box import Box


Call = Callable[[simpleobsws.Request], Awaitable[simpleobsws.RequestResponse]]


class ObsRequestBox(Box):
    """What the obs request boxes share (not a box itself: it has no run).

    SAMMI's OBS raw request: any obs-websocket request by its name, for what has no box of its own yet.
    Flow only, so no API caller can send OBS any request it likes."""

    def __init__(self, call: Call, protocol: ObsProtocol | None = None) -> None:
        self._call = call
        self._protocol = protocol or ObsProtocol()

    async def request_names(self) -> dict[str, dict[str, str]]:
        """By category (Scenes, Inputs, ...), only the requests this OBS has."""
        return self._protocol.by_category((await self._request("GetVersion"))["availableRequests"])

    async def _request(self, kind: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._call(simpleobsws.Request(kind, data))
        if not response.ok():
            raise ObsRequestError(kind, response.requestStatus.code, response.requestStatus.comment)
        return response.responseData or {}
