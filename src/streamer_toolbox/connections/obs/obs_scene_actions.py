from streamer_toolbox.connections.obs.boxes.get_transition import GetTransition
from streamer_toolbox.connections.obs.boxes.scene_sources import SceneSources
from streamer_toolbox.connections.obs.boxes.set_transition import SetTransition
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsSceneActions:
    """OBS boxes for scenes and transitions: which transition a scene switch uses (and how long it takes), and
    what is in a scene (each source, shown or not), e.g. to hide everything in a For each.

    One Box class per box, in boxes/."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SetTransition(self._requests), GetTransition(self._requests), SceneSources(self._requests)):
            actions.add_box(box, "obs")
