from streamer_toolbox.connections.obs.boxes.filter_on_off import FilterOnOff
from streamer_toolbox.connections.obs.boxes.is_filter_on import IsFilterOn
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsFilterActions:
    """OBS boxes for filters (a source's or scene's Filters window): switch one on / off / the other way, ask if
    it is on.

    One Box class per box, in boxes/."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (FilterOnOff(self._requests), IsFilterOn(self._requests)):
            actions.add_box(box, "obs")
