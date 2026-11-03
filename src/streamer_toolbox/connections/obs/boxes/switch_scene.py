from typing import TYPE_CHECKING

from streamer_toolbox.core.interfaces.box import Box

if TYPE_CHECKING:
    from streamer_toolbox.connections.obs_connection import ObsConnection


class SwitchScene(Box):
    name = "switch_scene"
    label = "Switch scene"
    help = "Switches OBS to a scene"
    group = "Scenes"

    def __init__(self, obs: "ObsConnection") -> None:
        self._obs = obs
        self.options = {"scene": self._obs.scene_names}

    async def run(self, scene: str) -> None:
        return await self._obs.switch_scene(scene)
