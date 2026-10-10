from typing import Any, Callable

import simpleobsws

from streamer_toolbox.connections.obs.lazy_obs_client import LazyObsClient
from streamer_toolbox.core.interfaces.obs_connection_checker import ObsConnectionChecker
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.connections.obs.obs_status import ObsStatus


class SimpleobswsConnectionChecker(ObsConnectionChecker):
    """ObsConnectionChecker over obs-websocket v5 with a fresh simpleobsws client per check."""

    def __init__(self, client_factory: Callable[[str, str], Any] = simpleobsws.WebSocketClient) -> None:
        self._client_factory = client_factory

    async def check(self, url: str, password: str) -> ObsStatus:
        client = self._client_factory(url, password)
        try:
            return await self.read(LazyObsClient(client))
        finally:
            if client.ws_open:
                await client.disconnect()

    async def read(self, client: LazyObsClient) -> ObsStatus:
        """The same read-only look, over a connection someone else keeps open."""
        version = await self._call(client, "GetVersion")
        profiles = await self._call(client, "GetProfileList")
        collections = await self._call(client, "GetSceneCollectionList")
        scenes = await self._call(client, "GetSceneList")
        return ObsStatus(
            obs_version=version.get("obsVersion", "?"),
            websocket_version=version.get("obsWebSocketVersion", "?"),
            profile=profiles.get("currentProfileName", "?"),
            scene_collection=collections.get("currentSceneCollectionName", "?"),
            # OBS lists scenes bottom-up; reversed matches the order in its Scenes dock
            scenes=tuple(s["sceneName"] for s in reversed(scenes.get("scenes", []))),
        )

    @staticmethod
    async def _call(client: LazyObsClient, request_type: str) -> dict:
        response = await client.call(simpleobsws.Request(request_type))
        if not response.ok():
            status = response.requestStatus
            raise ObsRequestError(request_type, status.code, status.comment)
        return response.responseData or {}
