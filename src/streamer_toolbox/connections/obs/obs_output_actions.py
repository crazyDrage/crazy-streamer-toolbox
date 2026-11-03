from streamer_toolbox.connections.obs.boxes.live_recording import LiveRecording
from streamer_toolbox.connections.obs.boxes.obs_hotkey import ObsHotkey
from streamer_toolbox.connections.obs.boxes.obs_stats import ObsStats
from streamer_toolbox.connections.obs.boxes.recording import Recording
from streamer_toolbox.connections.obs.boxes.replay_buffer import ReplayBuffer
from streamer_toolbox.connections.obs.boxes.screenshot import Screenshot
from streamer_toolbox.connections.obs.boxes.streaming import Streaming
from streamer_toolbox.connections.obs.boxes.virtual_camera import VirtualCamera
from streamer_toolbox.connections.obs.obs_requests import ObsRequests
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsOutputActions:
    """OBS boxes for what OBS sends out: recording, streaming, the replay buffer (save the last seconds as a
    clip), the virtual camera; a screenshot of a source or scene; OBS's own stats; and pressing one of OBS's
    hotkeys (anything set under Settings → Hotkeys, without a key).

    One Box class per box, in boxes/."""

    def __init__(self, requests: ObsRequests) -> None:
        self._requests = requests

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (Recording(self._requests), Streaming(self._requests), ReplayBuffer(self._requests),
                    VirtualCamera(self._requests), LiveRecording(self._requests), Screenshot(self._requests),
                    ObsStats(self._requests), ObsHotkey(self._requests)):
            actions.add_box(box, "obs")
