from streamer_toolbox.connections.obs.boxes.obs_output_box import ObsOutputBox, VIRTUAL_CAMERA, _choices, _request


class VirtualCamera(ObsOutputBox):
    name = "virtual_camera"
    label = "Virtual camera"
    help = "Starts or stops OBS's virtual camera"
    options = {"action": _choices(VIRTUAL_CAMERA)}
    group = "Recording / streaming"

    async def run(self, action: str = "toggle") -> None:
        await self._requests(_request(VIRTUAL_CAMERA, action))
