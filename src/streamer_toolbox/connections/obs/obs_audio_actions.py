from streamer_toolbox.connections.obs.boxes.get_audio_monitoring import GetAudioMonitoring
from streamer_toolbox.connections.obs.boxes.get_audio_tracks import GetAudioTracks
from streamer_toolbox.connections.obs.boxes.is_muted import IsMuted
from streamer_toolbox.connections.obs.boxes.mute_unmute import MuteUnmute
from streamer_toolbox.connections.obs.boxes.set_audio_monitoring import SetAudioMonitoring
from streamer_toolbox.connections.obs.boxes.set_audio_tracks import SetAudioTracks
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsAudioActions:
    """OBS boxes for what the Audio Mixer's ⋮ → Advanced Audio Properties shows: monitoring (hear it yourself:
    off / monitor only / monitor and output), which of the 6 audio tracks a source goes to (recording / VOD
    tracks), and mute.

    One Box class per box, in boxes/."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SetAudioMonitoring(self._requests), GetAudioMonitoring(self._requests),
                    SetAudioTracks(self._requests), GetAudioTracks(self._requests), MuteUnmute(self._requests),
                    IsMuted(self._requests)):
            actions.add_box(box, "obs")
