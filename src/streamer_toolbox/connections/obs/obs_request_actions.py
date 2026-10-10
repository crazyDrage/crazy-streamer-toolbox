import json
from collections.abc import Awaitable, Callable
from typing import Any

import simpleobsws

from streamer_toolbox.connections.obs.obs_protocol import ObsProtocol
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.core.actions.action_registry import ActionRegistry

Call = Callable[[simpleobsws.Request], Awaitable[simpleobsws.RequestResponse]]


class ObsRequestActions:
    """SAMMI's OBS raw request: any obs-websocket request by its name, for what has no box of its own yet.
    Flow only, so no API caller can send OBS any request it likes."""

    def __init__(self, call: Call, protocol: ObsProtocol | None = None) -> None:
        self._call = call
        self._protocol = protocol or ObsProtocol()

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("obs.request", self.request, "Sends OBS any request by name (see the obs-websocket protocol), "
                    "data as JSON text like {\"sceneName\": \"desktop\"}; picking a request fills in its fields. "
                    "The answer can be saved in a variable", "Raw request", group="Advanced",
                    options={"request": self.request_names}, flow_only=True,
                    fills={"request": self._protocol.template}, live_hints={"data": self._protocol.hint})

    async def request(self, request: str, data: Any = "") -> dict[str, Any]:
        if isinstance(data, str):
            try:
                data = json.loads(data) if data.strip() else None
            except ValueError as e:
                raise ValueError(f"data is not JSON text: {e}") from None
        if data is not None and not isinstance(data, dict):
            raise ValueError(f"data must be an object like {{\"name\": value}}, not {data!r}")
        return await self._request(request, data)

    async def request_names(self) -> dict[str, dict[str, str]]:
        """By category (Scenes, Inputs, ...), only the requests this OBS has."""
        return self._protocol.by_category((await self._request("GetVersion"))["availableRequests"])

    async def _request(self, kind: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._call(simpleobsws.Request(kind, data))
        if not response.ok():
            raise ObsRequestError(kind, response.requestStatus.code, response.requestStatus.comment)
        return response.responseData or {}
