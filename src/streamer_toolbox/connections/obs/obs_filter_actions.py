from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_bool


class ObsFilterActions:
    """OBS boxes for filters (a source's or scene's Filters window): switch one on / off / the other way, ask if
    it is on."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        sources = self._sources_with_filters
        actions.add("obs.set_filter", self.set_filter, "Switches a filter of a source or scene on, off or the "
                    "other way", "Filter on / off", group="Filters",
                    options={"source": sources, "filter": self._requests.filter_names, "state": _states})
        actions.add("obs.get_filter", self.get_filter, "Whether a filter is on (true / false)", "Is filter on",
                    group="Filters", options={"source": sources, "filter": self._requests.filter_names})

    async def set_filter(self, source: str, filter: str, state: str = "toggle") -> bool:
        on = not await self.get_filter(source, filter) if state == "toggle" else state != "off" and to_bool(state)
        await self._requests("SetSourceFilterEnabled", {"sourceName": source, "filterName": filter,
                                                        "filterEnabled": on})
        return on

    async def get_filter(self, source: str, filter: str) -> bool:
        answer = await self._requests("GetSourceFilter", {"sourceName": source, "filterName": filter})
        return bool(answer["filterEnabled"])

    async def _sources_with_filters(self) -> list[str]:
        return list(await self._requests.filter_names())


async def _states() -> list[str]:
    return ["on", "off", "toggle"]
