from streamer_toolbox.connections.obs.boxes.obs_audio_box import ObsAudioBox, MONITORING
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class GetAudioMonitoring(ObsAudioBox):
    name = "get_audio_monitoring"
    label = "Get audio monitoring"
    help = "A source's monitoring: off, monitor only or monitor and output"
    group = "Audio"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._requests.input_names}

    async def run(self, source: str) -> str:
        kind = (await self._requests("GetInputAudioMonitorType", {"inputName": source}))["monitorType"]
        return next((name for name, value in MONITORING.items() if value == kind), kind)
