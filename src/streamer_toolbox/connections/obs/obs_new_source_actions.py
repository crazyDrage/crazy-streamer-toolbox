from streamer_toolbox.connections.obs.boxes.create_source import CreateSource
from streamer_toolbox.connections.obs.boxes.remove_source import RemoveSource
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsNewSourceActions:
    """OBS boxes that make a new source in a scene (any kind, with its settings) and remove a source from OBS.

    One Box class per box, in boxes/."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (CreateSource(self._requests), RemoveSource(self._requests)):
            actions.add_box(box, "obs")
