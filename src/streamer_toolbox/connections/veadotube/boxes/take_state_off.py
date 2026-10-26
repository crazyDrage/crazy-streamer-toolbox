from streamer_toolbox.connections.veadotube.boxes.veadotube_box import VeadotubeBox
from streamer_toolbox.connections.veadotube.veadotube_client import VeadotubeClient


class TakeStateOff(VeadotubeBox):
    name = "pop_state"
    label = "Take state off"
    help = "Takes a state off again; what was under it shows"
    group = "Stack"

    def __init__(self, client: VeadotubeClient) -> None:
        super().__init__(client)
        self.options = {"state": self.state_names}

    async def run(self, state: str) -> None:
        await self._client.tell("pop", await self._id(state))
