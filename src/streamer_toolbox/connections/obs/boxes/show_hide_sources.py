from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox
from streamer_toolbox.core.data.box_value import to_bool, to_list


class ShowHideSources(ObsSceneBox):
    """His round 82: shows or hides every (scene, source) of a list at once, e.g. what Sources in scenes gives."""

    name = "set_sources_visible"
    label = "Show / hide sources"
    help = "Shows or hides every source of a list of {scene, source} (what Sources in scenes gives), all at once. " \
           "Gives how many it changed"
    group = "Sources"
    hints = {"places": "a list of {scene, source}, e.g. from Sources in scenes"}
    labels = {"places": "Sources"}

    async def run(self, places: Any, visible: bool = True) -> int:
        items = to_list(places) if not isinstance(places, dict) else [places]
        for place in items:
            if not isinstance(place, dict) or not place.get("scene") or not place.get("source"):
                raise ValueError(f"each one needs a scene and a source, like {{\"scene\": \"Gaming\", \"source\": "
                                 f"\"so-event\"}}, not {place!r}")
        for place in items:
            item = place.get("item_id")
            if not isinstance(item, int):
                item = await self._requests.scene_item_id(place["scene"], place["source"])
            await self._requests("SetSceneItemEnabled", {"sceneName": place["scene"], "sceneItemId": item,
                                                         "sceneItemEnabled": to_bool(visible)})
        return len(items)
