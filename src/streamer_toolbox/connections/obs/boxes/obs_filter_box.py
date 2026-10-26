from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.interfaces.box import Box


class ObsFilterBox(Box):
    """What the obs filter boxes share (not a box itself: it has no run).

    OBS boxes for filters (a source's or scene's Filters window): switch one on / off / the other way, ask if
    it is on."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    async def get_filter(self, source: str, filter: str) -> bool:
        answer = await self._requests("GetSourceFilter", {"sourceName": source, "filterName": filter})
        return bool(answer["filterEnabled"])

    async def _sources_with_filters(self) -> list[str]:
        return list(await self._requests.filter_names())


async def _states() -> list[str]:
    return ["on", "off", "toggle"]
