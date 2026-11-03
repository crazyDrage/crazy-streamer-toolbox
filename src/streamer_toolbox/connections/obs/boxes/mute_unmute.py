from streamer_toolbox.connections.obs.boxes.obs_audio_box import ObsAudioBox, _mute_choices
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.data.box_value import to_bool


class MuteUnmute(ObsAudioBox):
    name = "set_mute"
    label = "Mute / unmute"
    help = "Mutes or unmutes a source, or switches it the other way"
    group = "Audio"

    def __init__(self, requests: ObsRequests) -> None:
        super().__init__(requests)
        self.options = {"source": self._requests.input_names, "mute": _mute_choices}

    async def run(self, source: str, mute: str = "mute") -> bool:
        if mute == "toggle":
            return (await self._requests("ToggleInputMute", {"inputName": source}))["inputMuted"]
        muted = mute != "unmute" and to_bool(mute)
        await self._requests("SetInputMute", {"inputName": source, "inputMuted": muted})
        return muted
