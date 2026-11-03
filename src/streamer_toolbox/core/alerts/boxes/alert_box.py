from typing import Any

from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.files.file_types import IMAGE_TYPES, VIDEO_TYPES
from streamer_toolbox.core.interfaces.box import Box


PICTURE_TYPES = tuple(dict.fromkeys(IMAGE_TYPES + VIDEO_TYPES))


class AlertBox(Box):
    """What the alert boxes share (not a box itself: it has no run).

    The Alerts boxes: show an alert on the overlay (the Browser source in OBS that shows /overlay/alerts),
    empty the line."""

    def __init__(self, queue: AlertQueue) -> None:
        self._queue = queue


def _path(value: Any) -> str:
    """A file field's text: quotes from "Copy as path" taken off."""
    return str(value or "").strip().strip('"')
