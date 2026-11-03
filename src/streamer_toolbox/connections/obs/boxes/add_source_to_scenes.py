from typing import Any

from streamer_toolbox.connections.obs.boxes.copy_source import BOUNDS_KEYS, PLACE_KEYS
from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.data.box_value import to_bool, to_list


class AddSourceToScenes(ObsSceneBox):
    """His round 83: one source (the same one, so a video doesn't start again on a scene switch) into every scene
    a template source is in, where the template is; Take out of scenes cleans it up at the end."""

    name = "add_source_to_scenes"
    label = "Add source to scenes"
    help = "Puts a source that already exists into more scenes: the same source, not a copy, so a video goes on " \
           "playing when the scene changes. With a list from Sources in scenes it goes right above each one, in " \
           "its place and size. Gives the list of what it added (Take out of scenes takes it)"
    group = "Scenes"
    labels = {"places": "Where", "like": "Place like each one"}
    hints = {"source": "the source to add, e.g. clip-player",
             "places": "a list of {scene, source} (e.g. Sources in scenes of a template), or a scene's name"}

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._requests.source_names}

    async def run(self, source: str, places: Any, visible: bool = True, like: bool = True) -> list[dict[str, Any]]:
        source = str(source or "").strip()
        if not source:
            raise ValueError("which source to add?")
        added = []
        for place in _places(places):
            made = await self._requests("CreateSceneItem", {"sceneName": place["scene"], "sourceName": source,
                                                            "sceneItemEnabled": to_bool(visible)})
            new = made["sceneItemId"]
            if place.get("source") and to_bool(like):
                await self._place_like(place, new)
            added.append({"scene": place["scene"], "source": source, "item_id": new})
        return added

    async def _place_like(self, place: dict[str, Any], new: int) -> None:
        """The template's place, size and crop, and right above it."""
        scene, item = place["scene"], place.get("item_id")
        if not isinstance(item, int):
            item = await self._requests.scene_item_id(scene, place["source"])
        now = (await self._requests("GetSceneItemTransform", {"sceneName": scene, "sceneItemId": item}))
        now = now.get("sceneItemTransform", {})
        spot = {k: now[k] for k in PLACE_KEYS if k in now}
        if now.get("boundsType", "OBS_BOUNDS_NONE") != "OBS_BOUNDS_NONE":  # bounds of 0 are refused
            spot.update({k: now[k] for k in BOUNDS_KEYS if k in now})
        await self._requests("SetSceneItemTransform", {"sceneName": scene, "sceneItemId": new,
                                                       "sceneItemTransform": spot})
        index = (await self._requests("GetSceneItemIndex", {"sceneName": scene, "sceneItemId": item}))
        await self._requests("SetSceneItemIndex", {"sceneName": scene, "sceneItemId": new,
                                                   "sceneItemIndex": index["sceneItemIndex"] + 1})


def _places(places: Any) -> list[dict[str, Any]]:
    """{scene, source} dicts; a scene's name (or a list of them) is a scene without a template."""
    if isinstance(places, dict):
        items = [places]
    elif isinstance(places, str) and places.strip() and not places.strip().startswith("["):
        items = [places]
    else:
        items = to_list(places)
    out = [{"scene": p.strip()} if isinstance(p, str) and p.strip() else p for p in items]
    for place in out:
        if not isinstance(place, dict) or not place.get("scene"):
            raise ValueError(f"each one needs a scene, like {{\"scene\": \"Gaming\", \"source\": \"so-event\"}} or "
                             f"\"Gaming\", not {place!r}")
    return out
