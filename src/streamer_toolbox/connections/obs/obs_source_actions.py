from collections.abc import Awaitable, Callable
from typing import Any

import simpleobsws

from streamer_toolbox.connections.obs.keep_inside import keep_inside
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.file_types import IMAGE_TYPES, MEDIA_TYPES

Call = Callable[[simpleobsws.Request], Awaitable[simpleobsws.RequestResponse]]


MEDIA_ACTIONS = {"restart": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART",
                 "play": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PLAY",
                 "pause": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PAUSE",
                 "stop": "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_STOP"}


class ObsSourceActions:
    """OBS boxes for sources: show / hide one in a scene (SAMMI's Source Visibility), read / set an audio
    source's volume (0 = silent, 1 = full, like OBS's mixer slider in percent / 100), and for a Media Source: put
    a video file in it, size it, and restart / play / pause / stop it."""

    def __init__(self, call: Call) -> None:
        self._call = call

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("obs.set_source_visible", self.set_visible, "Shows or hides a source in a scene",
                    "Show / hide source", group="Sources",
                    options={"scene": self.scene_names, "source": self.source_names})
        actions.add("obs.set_volume", self.set_volume, "Sets an audio source's volume, 0 to 1", "Set volume",
                    group="Audio", options={"source": self.audio_names})
        actions.add("obs.set_media_file", self.set_media_file, "Puts a video (or sound) file into a Media Source. "
                    "Doesn't show it: use Show / hide source, then Media control → restart", "Set media file",
                    group="Media", options={"source": self.media_names}, files={"path": MEDIA_TYPES})
        actions.add("obs.set_image_file", self.set_image_file, "Puts a picture file into an Image source (like a meme "
                    "image on a soundboard button). Doesn't show it: use Show / hide source", "Set image file",
                    group="Media", options={"source": self.image_names}, files={"path": IMAGE_TYPES})
        actions.add("obs.set_source_size", self.set_source_size, "Sizes a source in a scene to width × height "
                    "(times scale, e.g. 0.5 for half), keeping where it is and its shape. Wire in the width and height "
                    "of Video info", "Set source size", group="Sources",
                    options={"scene": self.scene_names, "source": self.source_names},
                    labels={"keep_inside": "Keep inside the canvas"},
                    hints={"keep_inside": "on: if the new size sticks out (a tall video), it moves just enough to "
                                          "fit"},
                    outputs={"width": "number", "height": "number"})
        actions.add("obs.media_control", self.media_control, "Restarts, plays, pauses or stops a Media Source",
                    "Media control", group="Media",
                    options={"source": self.media_names, "action": self.media_action_names})
        actions.add("obs.get_volume", self.get_volume, "An audio source's volume, 0 to 1 (save it to put it back "
                    "later)", "Get volume", group="Audio", options={"source": self.audio_names})

    async def set_visible(self, scene: str, source: str, visible: bool = True) -> None:
        item = await self._request("GetSceneItemId", {"sceneName": scene, "sourceName": source})
        await self._request("SetSceneItemEnabled", {"sceneName": scene, "sceneItemId": item["sceneItemId"],
                                                    "sceneItemEnabled": _bool(visible)})

    async def set_volume(self, source: str, volume: float) -> None:
        await self._request("SetInputVolume", {"inputName": source, "inputVolumeMul": max(float(volume), 0.0)})

    async def get_volume(self, source: str) -> float:
        return (await self._request("GetInputVolume", {"inputName": source}))["inputVolumeMul"]

    async def set_media_file(self, source: str, path: str) -> None:
        await self._request("SetInputSettings", {"inputName": source, "inputSettings": {
            "local_file": str(path), "is_local_file": True}})

    async def set_image_file(self, source: str, path: str) -> None:
        await self._request("SetInputSettings", {"inputName": source, "inputSettings": {"file": str(path)}})

    async def set_source_size(self, scene: str, source: str, width: float, height: float,
                              scale: float = 1.0, keep_inside: bool = False) -> dict[str, float]:
        """Bounds of width × height (scaled), content fitted inside keeping its shape; the position stays, unless
        keep_inside and the new size would stick out of the canvas: then it moves just enough to fit."""
        size = {"width": round(float(width) * float(scale), 2), "height": round(float(height) * float(scale), 2)}
        if size["width"] <= 0 or size["height"] <= 0:
            raise ValueError(f"a size must be above 0, got {size['width']} × {size['height']}")
        item = await self._request("GetSceneItemId", {"sceneName": scene, "sourceName": source})
        transform = {"boundsType": "OBS_BOUNDS_SCALE_INNER", "boundsAlignment": 0,
                     "boundsWidth": size["width"], "boundsHeight": size["height"]}
        if _bool(keep_inside):
            transform.update(await self._inside(scene, item["sceneItemId"], size["width"], size["height"]))
        await self._request("SetSceneItemTransform", {
            "sceneName": scene, "sceneItemId": item["sceneItemId"], "sceneItemTransform": transform})
        return size

    async def _inside(self, scene: str, item: int, width: float, height: float) -> dict[str, float]:
        canvas = await self._request("GetVideoSettings")
        now = (await self._request("GetSceneItemTransform", {"sceneName": scene, "sceneItemId": item}))
        now = now.get("sceneItemTransform", {})
        x, y = keep_inside(float(now.get("positionX", 0)), float(now.get("positionY", 0)),
                           int(now.get("alignment", 5)), width, height, float(canvas["baseWidth"]),
                           float(canvas["baseHeight"]))
        return {"positionX": x, "positionY": y}

    async def media_control(self, source: str, action: str = "restart") -> None:
        if action not in MEDIA_ACTIONS:
            raise ValueError(f"unknown media action {action!r}; use one of {', '.join(MEDIA_ACTIONS)}")
        await self._request("TriggerMediaInputAction", {"inputName": source, "mediaAction": MEDIA_ACTIONS[action]})

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
