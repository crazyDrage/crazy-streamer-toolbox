import uuid
from typing import Any

from streamer_toolbox.connections.obs.obs_placement import ObsPlacement
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool

MARKER_COLOR = 0xB3FF5E6C  # OBS's colour number (alpha, blue, green, red): the toolbox purple, see-through
MARKER_SIZE = (640.0, 360.0)  # a new marker, until he sizes it


class ObsPlacementActions:
    """OBS boxes for a place in a scene (ObsPlacement): read a source's place, put a source at a place. The
    place of the Place source box is set up in its own window: a coloured marker appears in OBS, he drags and
    sizes it there, and the window takes over where it ended up (put_marker / take_marker, also boxes so the
    window and plugins use the same way in)."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        scenes_and_sources = {"scene": self._requests.scene_names, "source": self._requests.source_names}
        actions.add("obs.place_source", self.place_source, "Puts a source at a place in the scene: the spot and "
                    "size you set up once with a marker in OBS (Set up the place). The source is fitted into "
                    "that box, keeping its shape", "Place source", group="Sources", options=scenes_and_sources,
                    editors={"place": "obs_placement"})
        actions.add("obs.get_source_place", self.get_place, "Where a source sits in a scene: x, y, width, height "
                    "(as shown), rotation. Wire it into Place source to put another source there",
                    "Get source place", group="Sources", options=scenes_and_sources,
                    outputs={"x": "number", "y": "number", "width": "number", "height": "number",
                             "rotation": "number", "alignment": "number"})
        actions.add("obs.put_place_marker", self.put_marker, "Shows a coloured marker in a scene to drag and size "
                    "in OBS (at a place, if you give one). Take place marker reads where it ended up",
                    "Put place marker", group="Advanced", options={"scene": self._requests.scene_names},
                    outputs={"source": "text", "scene": "text"}, flow_only=True)
        actions.add("obs.take_place_marker", self.take_marker, "Reads where a place marker is now and removes "
                    "it; keep off = only remove it", "Take place marker", group="Advanced",
                    options={"scene": self._requests.scene_names},
                    outputs={"x": "number", "y": "number", "width": "number", "height": "number"}, flow_only=True)

    async def place_source(self, scene: str, source: str, place: Any) -> None:
        if place in (None, ""):
            raise ValueError("no place yet: Set up the place first (the button in this box)")
        await self.apply(scene, await self._requests.scene_item_id(scene, source), ObsPlacement.from_value(place))

    async def apply(self, scene: str, item: int, place: ObsPlacement) -> None:
        await self._requests("SetSceneItemTransform", {"sceneName": scene, "sceneItemId": item,
                                                       "sceneItemTransform": place.to_transform()})

    async def get_place(self, scene: str, source: str) -> dict[str, Any]:
        item = await self._requests.scene_item_id(scene, source)
        now = await self._requests("GetSceneItemTransform", {"sceneName": scene, "sceneItemId": item})
        return ObsPlacement.from_transform(now["sceneItemTransform"], scene).to_dict()

    async def put_marker(self, scene: str, place: Any = "") -> dict[str, Any]:
        """A see-through colour source on top of the scene, at `place` (its spot and size) or top left."""
        at = ObsPlacement.from_value(place) if place not in (None, "") else None
        width, height = (at.width, at.height) if at and at.width > 0 and at.height > 0 else MARKER_SIZE
        name = f"toolbox place marker {uuid.uuid4().hex[:6]}"
        made = await self._requests("CreateInput", {
            "sceneName": scene, "inputName": name, "inputKind": "color_source_v3", "sceneItemEnabled": True,
            "inputSettings": {"color": MARKER_COLOR, "width": round(width), "height": round(height)}})
        if at:
            try:  # only the spot: without bounds he sizes it by dragging its corners
                await self._requests("SetSceneItemTransform", {
                    "sceneName": scene, "sceneItemId": made["sceneItemId"],
                    "sceneItemTransform": {"positionX": at.x, "positionY": at.y, "rotation": at.rotation,
                                           "alignment": at.alignment}})
            except BaseException:
                await self._requests("RemoveInput", {"inputName": name})
                raise
        return {"source": name, "scene": scene}

    async def take_marker(self, scene: str, source: str, keep: bool = True) -> dict[str, Any]:
        """keep: the marker's place (read before it's removed); not keep: {} (Cancel)."""
        try:
            return await self.get_place(scene, source) if to_bool(keep) else {}
        finally:
            await self._requests("RemoveInput", {"inputName": source})
