from streamer_toolbox.connections.obs.boxes.obs_audio_box import ObsAudioBox, _monitoring, monitor_type
from streamer_toolbox.connections.obs.obs_requests import ObsRequests


class SetAudioMonitoring(ObsAudioBox):
    name = "set_audio_monitoring"
    label = "Set audio monitoring"
    help = "Whether you hear a source yourself: off, monitor only (you, not the stream) or monitor and output " \
           "(both)"
    group = "Audio"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._requests.input_names, "monitoring": _monitoring}

    async def run(self, source: str, monitoring: str = "monitor and output") -> None:
        await self._requests("SetInputAudioMonitorType", {"inputName": source,
                                                          "monitorType": monitor_type(monitoring)})
