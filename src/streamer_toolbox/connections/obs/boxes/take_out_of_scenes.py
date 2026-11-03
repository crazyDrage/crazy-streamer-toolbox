from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox
from streamer_toolbox.core.data.box_value import to_list


class TakeOutOfScenes(ObsSceneBox):
    """His round 83: "I need to clean up at the end": takes out what Add source to scenes put in."""

    name = "take_out_of_scenes"
    label = "Take out of scenes"
    help = "Takes every source of a list of {scene, source} out of its scene (what Add source to scenes gives). " \
           "The source itself stays in OBS and in its other scenes (Remove source removes it everywhere). Gives " \
           "how many it took out"
    group = "Scenes"
    hints = {"places": "a list of {scene, source}, e.g. from Add source to scenes"}
    labels = {"places": "Sources"}

    async def run(self, places: Any) -> int:
        items = to_list(places) if not isinstance(places, dict) else [places]
        for place in items:
            if not isinstance(place, dict) or not place.get("scene") or not place.get("source"):
                raise ValueError(f"each one needs a scene and a source, like {{\"scene\": \"Gaming\", \"source\": "
                                 f"\"clip-player\"}}, not {place!r}")
        for place in items:
            item = place.get("item_id")
            if not isinstance(item, int):
                item = await self._requests.scene_item_id(place["scene"], place["source"])
            await self._requests("RemoveSceneItem", {"sceneName": place["scene"], "sceneItemId": item})
        return len(items)
