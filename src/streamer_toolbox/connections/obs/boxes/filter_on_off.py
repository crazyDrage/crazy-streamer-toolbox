from streamer_toolbox.connections.obs.boxes.obs_filter_box import ObsFilterBox, _states
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.data.box_value import to_bool


class FilterOnOff(ObsFilterBox):
    name = "set_filter"
    label = "Filter on / off"
    help = "Switches a filter of a source or scene on, off or the other way"
    group = "Filters"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._sources_with_filters, "filter": self._requests.filter_names, "state": _states}

    async def run(self, source: str, filter: str, state: str = "toggle") -> bool:
        on = not await self.get_filter(source, filter) if state == "toggle" else state != "off" and to_bool(state)
        await self._requests("SetSourceFilterEnabled", {"sourceName": source, "filterName": filter,
                                                        "filterEnabled": on})
        return on
