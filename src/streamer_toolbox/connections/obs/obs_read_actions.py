from streamer_toolbox.connections.obs.boxes.get_preview_scene import GetPreviewScene
from streamer_toolbox.connections.obs.boxes.get_profile import GetProfile
from streamer_toolbox.connections.obs.boxes.get_scene_collection import GetSceneCollection
from streamer_toolbox.connections.obs.boxes.is_studio_mode_on import IsStudioModeOn
from streamer_toolbox.connections.obs.boxes.scene_list import SceneList
from streamer_toolbox.connections.obs.boxes.source_list import SourceList
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsReadActions:
    """OBS boxes that only read what OBS has now, without fields (each also a Live value): the scenes, the
    sources, studio mode and its preview scene, the profile and the scene collection in use.

    One Box class per box, in boxes/."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SceneList(self._requests), SourceList(self._requests), IsStudioModeOn(self._requests),
                    GetPreviewScene(self._requests), GetProfile(self._requests),
                    GetSceneCollection(self._requests)):
            actions.add_box(box, "obs")
