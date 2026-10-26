from collections.abc import Awaitable, Callable
from typing import Any

import simpleobsws

from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.core.interfaces.box import Box


Call = Callable[[simpleobsws.Request], Awaitable[simpleobsws.RequestResponse]]
TEXT_KINDS = ("text_gdiplus_v3", "text_gdiplus_v2", "text_gdiplus", "text_ft2_source_v2", "text_ft2_source")


class ObsInputBox(Box):
    """What the obs input boxes share (not a box itself: it has no run).

    OBS boxes for a source's own settings and its place in a scene: set a Text source's text (SAMMI's Set
    Text), read / change any setting (what the source's Properties window shows), move a source."""

    def __init__(self, call: Call) -> None:
        self._call = call

    async def text_names(self) -> list[str]:
        inputs = (await self._request("GetInputList"))["inputs"]
        return sorted((i["inputName"] for i in inputs if i.get("inputKind") in TEXT_KINDS), key=str.casefold)

    async def input_names(self) -> list[str]:
        return sorted((i["inputName"] for i in (await self._request("GetInputList"))["inputs"]), key=str.casefold)

    async def scene_names(self) -> list[str]:
        return [s["sceneName"] for s in reversed((await self._request("GetSceneList"))["scenes"])]

    async def source_names(self) -> list[str]:
        names = set()
        for scene in await self.scene_names():
            items = await self._request("GetSceneItemList", {"sceneName": scene})
            names.update(i["sourceName"] for i in items["sceneItems"])
        return sorted(names, key=str.casefold)

    async def _request(self, kind: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._call(simpleobsws.Request(kind, data))
        if not response.ok():
            raise ObsRequestError(kind, response.requestStatus.code, response.requestStatus.comment)
        return response.responseData or {}


def _source_name(source: Any) -> str:
    """The source's name from what was wired in: Create source's whole result works too; its item_id doesn't
    (OBS finds a source's settings by name)."""
    if isinstance(source, dict) and "source" in source:
        return str(source["source"])
    if isinstance(source, (int, float, dict, list)):
        raise ValueError(f"source is the source's name, not {source!r}: from Create source take 'source', not "
                         "'item_id'")
    return source
