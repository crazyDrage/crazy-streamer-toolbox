from streamer_toolbox.connections.obs.boxes.obs_output_box import ObsOutputBox, STREAM, _choices, _request


class Streaming(ObsOutputBox):
    name = "stream"
    label = "Streaming"
    help = "Starts or stops the stream (careful: stop ends your stream)"
    options = {"action": _choices(STREAM)}
    group = "Recording / streaming"

    async def run(self, action: str = "toggle") -> None:
        await self._requests(_request(STREAM, action))
