from streamer_toolbox.connections.obs.boxes.get_source_place import GetSourcePlace
from streamer_toolbox.connections.obs.boxes.place_source import PlaceSource
from streamer_toolbox.connections.obs.boxes.put_place_marker import PutPlaceMarker
from streamer_toolbox.connections.obs.boxes.take_place_marker import TakePlaceMarker
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsPlacementActions:
    """OBS boxes for a place in a scene (ObsPlacement): read a source's place, put a source at a place. The
    place of the Place source box is set up in its own window: a coloured marker appears in OBS, he drags and
    sizes it there, and the window takes over where it ended up (put_marker / take_marker, also boxes so the
    window and plugins use the same way in).

    One Box class per box, in boxes/."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (PlaceSource(self._requests), GetSourcePlace(self._requests), PutPlaceMarker(self._requests),
                    TakePlaceMarker(self._requests)):
            actions.add_box(box, "obs")
