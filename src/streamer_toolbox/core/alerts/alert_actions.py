from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.files.file_types import AUDIO_TYPES, IMAGE_TYPES, VIDEO_TYPES

PICTURE_TYPES = tuple(dict.fromkeys(IMAGE_TYPES + VIDEO_TYPES))


class AlertActions:
    """The Alerts boxes: show an alert on the overlay (the Browser source in OBS that shows /overlay/alerts),
    empty the line."""

    def __init__(self, queue: AlertQueue) -> None:
        self._queue = queue

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("alert.show", self.show, "Shows an alert on the overlay (a Browser source in OBS, its address "
                    "is on the Overlay page): a line of text, a picture / gif / video, a sound. Alerts wait in "
                    "line, one at a time", "Show alert", group="Alerts",
                    labels={"image": "Picture or video", "wait": "Wait until it was shown"},
                    hints={"text": "e.g. ${event.user} just followed!",
                           "highlight": "the part of the text to colour, e.g. ${event.user}",
                           "seconds": "how long it stays", "volume": "0 to 1",
                           "message": "a smaller second line, e.g. ${event.message}"},
                    files={"image": PICTURE_TYPES, "sound": AUDIO_TYPES},
                    outputs={"overlays": "number", "in_front": "number"})
        actions.add("alert.clear", self.clear, "Empties the alert line and takes the alert that is showing away; "
                    "gives how many were dropped", "Clear alerts", group="Alerts")

    async def show(self, text: str = "", image: str = "", sound: str = "", seconds: float = 5.0,
                   volume: float = 1.0, highlight: str = "", wait: bool = False,
                   message: str = "") -> dict[str, Any]:
        if not (str(text).strip() or str(image).strip() or str(sound).strip()):
            raise ValueError("an alert needs a text, a picture or a sound")
        alert = Alert(str(text), _path(image), _path(sound), float(seconds), float(volume), (str(highlight),),
                      str(message))
        return {"overlays": self._queue.overlays, "in_front": await self._queue.show(alert, to_bool(wait))}

    async def clear(self) -> int:
        return self._queue.clear()


def _path(value: Any) -> str:
    """A file field's text: quotes from "Copy as path" taken off."""
    return str(value or "").strip().strip('"')
