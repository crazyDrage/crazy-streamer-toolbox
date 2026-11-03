from streamer_toolbox.connections.veadotube.boxes.veadotube_box import VeadotubeBox
from streamer_toolbox.connections.veadotube.veadotube_client import VeadotubeClient


class PutStateOnTop(VeadotubeBox):
    name = "push_state"
    label = "Put state on top"
    help = "Puts a state on top (it shows) until Take state off removes it"
    group = "Stack"

    def __init__(self, client: VeadotubeClient) -> None:
        super().__init__(client)
        self.options = {"state": self.state_names}

    async def run(self, state: str) -> None:
        await self._client.tell("push", await self._id(state))
