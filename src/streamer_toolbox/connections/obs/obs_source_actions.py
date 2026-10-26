from streamer_toolbox.connections.obs.boxes.get_volume import GetVolume
from streamer_toolbox.connections.obs.boxes.is_source_shown import IsSourceShown
from streamer_toolbox.connections.obs.boxes.media_control import MediaControl
from streamer_toolbox.connections.obs.boxes.obs_source_box import Call
from streamer_toolbox.connections.obs.boxes.set_image_file import SetImageFile
from streamer_toolbox.connections.obs.boxes.set_media_file import SetMediaFile
from streamer_toolbox.connections.obs.boxes.set_source_size import SetSourceSize
from streamer_toolbox.connections.obs.boxes.set_volume import SetVolume
from streamer_toolbox.connections.obs.boxes.show_hide_source import ShowHideSource
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsSourceActions:
    """OBS boxes for sources: show / hide one in a scene (SAMMI's Source Visibility) or ask if it is shown, read /
    set an audio source's volume (0 = silent, 1 = full, like OBS's mixer slider in percent / 100), and for a Media
    Source: put a video file in it, size it, and restart / play / pause / stop it.

    One Box class per box, in boxes/."""

    def __init__(self, call: Call) -> None:
        self._call = call

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (ShowHideSource(self._call), SetVolume(self._call), SetMediaFile(self._call),
                    SetImageFile(self._call), SetSourceSize(self._call), MediaControl(self._call),
                    GetVolume(self._call), IsSourceShown(self._call)):
            actions.add_box(box, "obs")
