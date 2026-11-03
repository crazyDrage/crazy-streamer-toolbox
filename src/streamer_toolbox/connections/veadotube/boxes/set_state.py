from streamer_toolbox.connections.veadotube.boxes.veadotube_box import VeadotubeBox
from streamer_toolbox.connections.veadotube.veadotube_client import VeadotubeClient


class SetState(VeadotubeBox):
    name = "set_state"
    label = "Set state"
    help = "Switches the avatar to a state"

    def __init__(self, client: VeadotubeClient) -> None:
        super().__init__(client)
        self.options = {"state": self.state_names}

    async def run(self, state: str) -> None:
        await self._client.tell("set", await self._id(state))
