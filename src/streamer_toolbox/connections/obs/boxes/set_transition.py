from typing import Any

from streamer_toolbox.connections.obs.boxes.obs_scene_box import ObsSceneBox
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class SetTransition(ObsSceneBox):
    name = "set_transition"
    label = "Set transition"
    help = "Picks the transition scene switches use (Fade, Cut, a stinger, ...) and how long it takes"
    hints = {"seconds": "empty = as it is (a Cut or a stinger has its own length)"}
    group = "Scenes"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"transition": self.transition_names}

    async def run(self, transition: str, seconds: Any = "") -> None:
        milliseconds = round(float(seconds) * 1000) if str(seconds).strip() != "" else None
        if milliseconds is not None and not 50 <= milliseconds <= 20000:  # checked first: nothing half done
            raise ValueError(f"OBS takes 0.05 to 20 seconds for a transition, not {seconds}")
        await self._requests("SetCurrentSceneTransition", {"transitionName": transition})
        if milliseconds is not None:
            await self._requests("SetCurrentSceneTransitionDuration", {"transitionDuration": milliseconds})
