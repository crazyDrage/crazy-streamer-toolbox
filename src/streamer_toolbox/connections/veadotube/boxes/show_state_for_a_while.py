import asyncio

from streamer_toolbox.connections.veadotube.boxes.veadotube_box import VeadotubeBox
from streamer_toolbox.connections.veadotube.veadotube_client import VeadotubeClient


class ShowStateForAWhile(VeadotubeBox):
    name = "show_state"
    label = "Show state for a while"
    help = "Shows a state for some seconds, then goes back to what was shown before"

    def __init__(self, client: VeadotubeClient) -> None:
        super().__init__(client)
        self.options = {"state": self.state_names}

    async def run(self, state: str, seconds: float = 3.0) -> None:
        state_id = await self._id(state)
        await self._client.tell("push", state_id)
        try:
            await asyncio.sleep(max(float(seconds), 0))
        finally:
            await self._client.tell("pop", state_id)
