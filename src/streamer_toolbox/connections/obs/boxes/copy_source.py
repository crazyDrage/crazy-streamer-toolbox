from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_new_source_box import ObsNewSourceBox
from streamer_toolbox.connections.obs.obs_request_error import ObsRequestError
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.data.box_value import to_bool

# what SetSceneItemTransform takes back of what GetSceneItemTransform gives (the rest it works out itself)
PLACE_KEYS = ("positionX", "positionY", "rotation", "scaleX", "scaleY", "alignment", "cropLeft", "cropRight",
              "cropTop", "cropBottom", "cropToBounds")
BOUNDS_KEYS = ("boundsType", "boundsWidth", "boundsHeight", "boundsAlignment")
# (read request, its answer's key, write request, its field) per audio setting
AUDIO = (("GetInputVolume", "inputVolumeMul", "SetInputVolume", "inputVolumeMul"),
         ("GetInputMute", "inputMuted", "SetInputMute", "inputMuted"),
         ("GetInputAudioMonitorType", "monitorType", "SetInputAudioMonitorType", "monitorType"),
         ("GetInputAudioTracks", "inputAudioTracks", "SetInputAudioTracks", "inputAudioTracks"),
         ("GetInputAudioBalance", "inputAudioBalance", "SetInputAudioBalance", "inputAudioBalance"),
         ("GetInputAudioSyncOffset", "inputAudioSyncOffset", "SetInputAudioSyncOffset", "inputAudioSyncOffset"))


class CopySource(ObsNewSourceBox):
    """His round 82: a copy of a source "with settings, audio settings, position, and anything else". OBS's own
    Copy + Paste (Duplicate) makes a source of its own the same way; Paste (Reference) would share it."""

    name = "copy_source"
    label = "Copy source"
    help = "A new source just like another one: its settings, its audio (volume, mute, monitoring, tracks, " \
           "balance, sync), its filters, and in the scene its place, size, crop, shown or not, blend mode and lock. " \
           "It is a source of its own: changing one doesn't change the other"
    group = "Sources"
    labels = {"to_scene": "Into scene", "filters": "Filters too"}
    hints = {"scene": "the scene the source is in (its place is copied from there)",
             "name": "must be new: OBS has no two sources with one name",
             "to_scene": "empty = the same scene, right above the original"}
    outputs = {"source": "text", "scene": "text", "item_id": "number"}

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"scene": self._requests.scene_names, "source": self._requests.source_names,
                        "to_scene": self._requests.scene_names}

    async def run(self, scene: str, source: str, name: str, to_scene: str = "",
                  filters: bool = True) -> dict[str, Any]:
        name, target = str(name).strip(), str(to_scene).strip() or scene
        if not name:
            raise ValueError("the copy needs a name")
        try:
            original = await self._requests("GetInputSettings", {"inputName": source})
        except ObsRequestError:
            raise ValueError(f"{source!r} isn't a source OBS knows (a scene or group can't be copied)") from None
        item = await self._requests.scene_item_id(scene, source)
        shown = (await self._requests("GetSceneItemEnabled", {"sceneName": scene, "sceneItemId": item}))
        made = await self._requests("CreateInput", {
            "sceneName": target, "inputName": name, "inputKind": original["inputKind"],
            "inputSettings": original.get("inputSettings", {}), "sceneItemEnabled": shown["sceneItemEnabled"]})
        new = made["sceneItemId"]
        await self._audio(source, name)
        if to_bool(filters):
            await self._filters(source, name)
        await self._scene_item(scene, item, target, new)
        return {"source": name, "scene": target, "item_id": new}

    async def _audio(self, source: str, name: str) -> None:
        """Every audio setting the original has; a source without sound answers none of them."""
        for read, key, write, field in AUDIO:
            try:
                value = (await self._requests(read, {"inputName": source}))[key]
            except (ObsRequestError, KeyError):
                continue
            await self._requests(write, {"inputName": name, field: value})

    async def _filters(self, source: str, name: str) -> None:
        for one in (await self._requests("GetSourceFilterList", {"sourceName": source})).get("filters", []):
            await self._requests("CreateSourceFilter", {
                "sourceName": name, "filterName": one["filterName"], "filterKind": one["filterKind"],
                "filterSettings": one.get("filterSettings", {})})
            if not one.get("filterEnabled", True):
                await self._requests("SetSourceFilterEnabled", {"sourceName": name, "filterName": one["filterName"],
                                                                "filterEnabled": False})

    async def _scene_item(self, scene: str, item: int, target: str, new: int) -> None:
        """Place, size and crop, blend mode, lock; in the same scene right above the original."""
        now = (await self._requests("GetSceneItemTransform", {"sceneName": scene, "sceneItemId": item}))
        now = now.get("sceneItemTransform", {})
        place = {k: now[k] for k in PLACE_KEYS if k in now}
        if now.get("boundsType", "OBS_BOUNDS_NONE") != "OBS_BOUNDS_NONE":  # bounds of 0 are refused
            place.update({k: now[k] for k in BOUNDS_KEYS if k in now})
        await self._requests("SetSceneItemTransform", {"sceneName": target, "sceneItemId": new,
                                                       "sceneItemTransform": place})
        for read, key, write in (("GetSceneItemBlendMode", "sceneItemBlendMode", "SetSceneItemBlendMode"),
                                 ("GetSceneItemLocked", "sceneItemLocked", "SetSceneItemLocked")):
            try:
                value = (await self._requests(read, {"sceneName": scene, "sceneItemId": item}))[key]
            except (ObsRequestError, KeyError):
                continue
            await self._requests(write, {"sceneName": target, "sceneItemId": new, key: value})
        if target == scene:
            index = (await self._requests("GetSceneItemIndex", {"sceneName": scene, "sceneItemId": item}))
            await self._requests("SetSceneItemIndex", {"sceneName": scene, "sceneItemId": new,
                                                       "sceneItemIndex": index["sceneItemIndex"] + 1})
