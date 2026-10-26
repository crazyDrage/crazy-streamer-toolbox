from streamer_toolbox.connections.obs.boxes.get_source_settings import GetSourceSettings
from streamer_toolbox.connections.obs.boxes.move_source import MoveSource
from streamer_toolbox.connections.obs.boxes.obs_input_box import Call
from streamer_toolbox.connections.obs.boxes.set_source_settings import SetSourceSettings
from streamer_toolbox.connections.obs.boxes.set_text import SetText
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class ObsInputActions:
    """OBS boxes for a source's own settings and its place in a scene: set a Text source's text (SAMMI's Set
    Text), read / change any setting (what the source's Properties window shows), move a source.

    One Box class per box, in boxes/."""

    def __init__(self, call: Call) -> None:
        self._call = call

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SetText(self._call), GetSourceSettings(self._call), SetSourceSettings(self._call),
                    MoveSource(self._call)):
            actions.add_box(box, "obs")
