from collections.abc import Awaitable, Callable
from typing import Any

import simpleobsws

from streamer_toolbox.connections.obs.keep_inside import keep_inside
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.core.interfaces.box import Box


Call = Callable[[simpleobsws.Request], Awaitable[simpleobsws.RequestResponse]]
MEDIA_ACTIONS = {"restart": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART",
                 "play": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PLAY",
                 "pause": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PAUSE",
                 "stop": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_STOP"}


class ObsSourceBox(Box):
    """What the obs source boxes share (not a box itself: it has no run).

    OBS boxes for sources: show / hide one in a scene (SAMMI's Source Visibility), read / set an audio
    source's volume (0 = silent, 1 = full, like OBS's mixer slider in percent / 100), and for a Media Source: put
    a video file in it, size it, and restart / play / pause / stop it."""

    def __init__(self, call: Call) -> None:
        self._call = call

    async def _inside(self, scene: str, item: int, width: float, height: float) -> dict[str, float]:
        canvas = await self._request("GetVideoSettings")
        now = (await self._request("GetSceneItemTransform", {"sceneName": scene, "sceneItemId": item}))
        now = now.get("sceneItemTransform", {})
        x, y = keep_inside(float(now.get("positionX", 0)), float(now.get("positionY", 0)),
                           int(now.get("alignment", 5)), width, height, float(canvas["baseWidth"]),
                           float(canvas["baseHeight"]))
        return {"positionX": x, "positionY": y}

    @staticmethod
    async def media_action_names() -> list[str]:
        return list(MEDIA_ACTIONS)

    async def media_names(self) -> list[str]:
        inputs = (await self._request("GetInputList"))["inputs"]
        media = [i["inputName"] for i in inputs if i.get("inputKind") in ("ffmpeg_source", "vlc_source")]
        return sorted(media, key=str.casefold)

    async def image_names(self) -> list[str]:
        inputs = (await self._request("GetInputList"))["inputs"]
        return sorted((i["inputName"] for i in inputs if i.get("inputKind") == "image_source"), key=str.casefold)

    async def scene_names(self) -> list[str]:
        return [s["sceneName"] for s in reversed((await self._request("GetSceneList"))["scenes"])]

    async def source_names(self) -> list[str]:
        names = set()
        for scene in await self.scene_names():
            items = await self._request("GetSceneItemList", {"sceneName": scene})
            names.update(i["sourceName"] for i in items["sceneItems"])
        return sorted(names, key=str.casefold)

    async def audio_names(self) -> list[str]:
        inputs = (await self._request("GetInputList"))["inputs"]
        return sorted((i["inputName"] for i in inputs), key=str.casefold)

    async def _request(self, kind: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._call(simpleobsws.Request(kind, data))
        if not response.ok():
            raise ObsRequestError(kind, response.requestStatus.code, response.requestStatus.comment)
        return response.responseData or {}


def _bool(value: Any) -> bool:
    """A box field may hold "false" as text."""
    if isinstance(value, str):
        return value.strip().casefold() not in ("false", "0", "no", "off", "")
    return bool(value)
