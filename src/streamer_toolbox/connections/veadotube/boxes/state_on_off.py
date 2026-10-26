from streamer_toolbox.connections.veadotube.boxes.veadotube_box import VeadotubeBox
from streamer_toolbox.connections.veadotube.veadotube_client import VeadotubeClient


class StateOnOff(VeadotubeBox):
    name = "toggle_state"
    label = "State on / off"
    help = "Puts a state on top, or takes it off when it is there"
    group = "Stack"

    def __init__(self, client: VeadotubeClient) -> None:
        super().__init__(client)
        self.options = {"state": self.state_names}

    async def run(self, state: str) -> None:
        await self._client.tell("toggle", await self._id(state))
