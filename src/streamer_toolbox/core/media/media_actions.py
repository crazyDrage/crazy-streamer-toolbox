from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.media.boxes.keep_media_locally import KeepMediaLocally
from streamer_toolbox.core.media.media_buffer import MediaBuffer


class MediaActions:
    """Boxes for media from the web: Keep media locally (MediaBuffer). One Box class per box, in boxes/."""

    def __init__(self, buffer: MediaBuffer) -> None:
        self._buffer = buffer

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (KeepMediaLocally(self._buffer),):
            actions.add_box(box, "media")
