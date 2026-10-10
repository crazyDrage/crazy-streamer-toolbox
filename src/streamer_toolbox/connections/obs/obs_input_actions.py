from collections.abc import Awaitable, Callable
from typing import Any

import simpleobsws

from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_kind

Call = Callable[[simpleobsws.Request], Awaitable[simpleobsws.RequestResponse]]
TEXT_KINDS = ("text_gdiplus_v3", "text_gdiplus_v2", "text_gdiplus", "text_ft2_source_v2", "text_ft2_source")


class ObsInputActions:
    """OBS boxes for a source's own settings and its place in a scene: set a Text source's text (SAMMI's Set
    Text), read / change any setting (what the source's Properties window shows), move a source."""

    def __init__(self, call: Call) -> None:
        self._call = call

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("obs.set_text", self.set_text, "Puts text into a Text source (e.g. 'Tracking Lost!')",
                    "Set text", group="Sources", options={"source": self.text_names})
        actions.add("obs.get_source_settings", self.get_settings, "A source's settings as an object (what its "
                    "Properties window shows, e.g. file, text, url)", "Get source settings", group="Sources",
                    options={"source": self.input_names})
        actions.add("obs.set_source_settings", self.set_settings, "Changes some settings of a source; settings = "
                    "an object like {\"url\": \"...\"}. The others stay", "Set source settings", group="Sources",
                    options={"source": self.input_names})
        actions.add("obs.move_source", self.move_source, "Moves a source in a scene to x / y (pixels from the top "
                    "left of the canvas); an empty one stays", "Move source", group="Sources",
                    options={"scene": self.scene_names, "source": self.source_names},
                    outputs={"x": "number", "y": "number"})

    async def set_text(self, source: str, text: str = "") -> None:
        await self._request("SetInputSettings", {"inputName": source, "inputSettings": {"text": str(text)}})

    async def get_settings(self, source: str) -> dict[str, Any]:
        name = _source_name(source)
        return (await self._request("GetInputSettings", {"inputName": name})).get("inputSettings", {})

    async def set_settings(self, source: str, settings: Any) -> None:
        try:
            changes = to_kind(settings, "object")
        except ValueError:
            raise ValueError(f"settings must be an object like {{\"text\": \"hi\"}}, not {settings!r}") from None
        await self._request("SetInputSettings", {"inputName": _source_name(source), "inputSettings": changes,
                                                 "overlay": True})

    async def move_source(self, scene: str, source: str, x: float | None = None,
                          y: float | None = None) -> dict[str, float]:
        item = (await self._request("GetSceneItemId", {"sceneName": scene, "sourceName": source}))["sceneItemId"]
        now = (await self._request("GetSceneItemTransform", {"sceneName": scene, "sceneItemId": item}))
        transform = now.get("sceneItemTransform", {})
        place = {"positionX": float(transform.get("positionX", 0)) if x in (None, "") else float(x),
                 "positionY": float(transform.get("positionY", 0)) if y in (None, "") else float(y)}
        await self._request("SetSceneItemTransform", {"sceneName": scene, "sceneItemId": item,
                                                      "sceneItemTransform": place})
        return {"x": place["positionX"], "y": place["positionY"]}

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
