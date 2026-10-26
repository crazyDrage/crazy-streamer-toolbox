from streamer_toolbox.connections.veadotube.boxes.veadotube_box import VeadotubeBox


class GetState(VeadotubeBox):
    name = "get_state"
    label = "Get state"
    help = "The name of the state the avatar shows now"
    outputs = {"state": "text"}

    async def run(self) -> dict[str, str]:
        if not self._client.current:
            raise ConnectionError("veadotube mini is not connected")
        return {"state": self._client.current}
