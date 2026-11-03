from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.interfaces.box import Box


class ObsSceneBox(Box):
    """What the obs scene boxes share (not a box itself: it has no run).

    OBS boxes for scenes and transitions: which transition a scene switch uses (and how long it takes), and
    what is in a scene (each source, shown or not), e.g. to hide everything in a For each."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    async def transition_names(self) -> list[str]:
        return [t["transitionName"] for t in (await self._requests("GetSceneTransitionList"))["transitions"]]
