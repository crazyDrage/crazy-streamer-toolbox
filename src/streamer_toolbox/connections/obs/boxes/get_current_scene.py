from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.obs_connection import ObsConnection


class GetCurrentScene(Box):
    name = "get_current_scene"
    label = "Get current scene"
    help = "The name of the scene that is live now"
    group = "Scenes"
    live = True

    def __init__(self, obs: "ObsConnection") -> None:
        self._obs = obs

    async def run(self) -> str:
        return await self._obs.current_scene()
