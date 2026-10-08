from collections.abc import Awaitable, Callable
from typing import Any

import simpleobsws

from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError

Call = Callable[[simpleobsws.Request], Awaitable[simpleobsws.RequestResponse]]
MEDIA_KINDS = ("ffmpeg_source", "vlc_source")


class ObsRequests:
    """One obs-websocket request with its answer (a failure raises ObsRequestError), and the name lists the box
    pickers share: scenes, sources (inputs), media sources, filters by source."""

    def __init__(self, call: Call) -> None:
        self._call = call

    async def __call__(self, kind: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._call(simpleobsws.Request(kind, data))
        if not response.ok():
            raise ObsRequestError(kind, response.requestStatus.code, response.requestStatus.comment)
        return response.responseData or {}

    async def scene_names(self) -> list[str]:
        return [s["sceneName"] for s in reversed((await self("GetSceneList"))["scenes"])]

    async def input_names(self) -> list[str]:
        return sorted((i["inputName"] for i in (await self("GetInputList"))["inputs"]), key=str.casefold)

    async def media_names(self) -> list[str]:
        inputs = (await self("GetInputList"))["inputs"]
        return sorted((i["inputName"] for i in inputs if i.get("inputKind") in MEDIA_KINDS), key=str.casefold)

    async def source_names(self) -> list[str]:
        """Everything that can sit in a scene: sources and the scenes themselves (a scene in a scene)."""
        names = set()
        for scene in await self.scene_names():
            items = await self("GetSceneItemList", {"sceneName": scene})
            names.update(i["sourceName"] for i in items["sceneItems"])
        return sorted(names, key=str.casefold)

    async def filter_names(self) -> dict[str, dict[str, str]]:
        """source → {filter: filter}: the field gets a source picker first. Sources without filters are left out."""
        groups: dict[str, dict[str, str]] = {}
        for source in await self.scene_names() + await self.input_names():
            filters = (await self("GetSourceFilterList", {"sourceName": source})).get("filters", [])
            if filters:
                groups[source] = {f["filterName"]: f["filterName"] for f in filters}
        return groups

    async def scene_item_id(self, scene: str, source: str) -> int:
        return (await self("GetSceneItemId", {"sceneName": scene, "sourceName": source}))["sceneItemId"]
