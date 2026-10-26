from streamer_toolbox.connections.obs.boxes.obs_filter_box import ObsFilterBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class IsFilterOn(ObsFilterBox):
    name = "get_filter"
    label = "Is filter on"
    help = "Whether a filter is on (true / false)"
    group = "Filters"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._sources_with_filters, "filter": self._requests.filter_names}

    async def run(self, source: str, filter: str) -> bool:
        return await self.get_filter(source, filter)
