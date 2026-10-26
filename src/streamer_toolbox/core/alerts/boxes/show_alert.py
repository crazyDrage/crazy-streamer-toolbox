from typing import Any

from streamer_toolbox.core.alerts.alert import Alert
from streamer_toolbox.core.alerts.boxes.alert_box import AlertBox, PICTURE_TYPES, _path
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.files.file_types import AUDIO_TYPES


class ShowAlert(AlertBox):
    name = "show"
    label = "Show alert"
    help = "Shows an alert on the overlay (a Browser source in OBS, its address is on the Overlay page): a line " \
           "of text, a picture / gif / video, a sound. Alerts wait in line, one at a time"
    group = "Alerts"
    labels = {"image": "Picture or video", "wait": "Wait until it was shown"}
    hints = {"text": "e.g. ${event.user} just followed!",
             "highlight": "the part of the text to colour, e.g. ${event.user}",
             "seconds": "how long it stays", "volume": "0 to 1",
             "message": "a smaller second line, e.g. ${event.message}"}
    files = {"image": PICTURE_TYPES, "sound": AUDIO_TYPES}
    outputs = {"overlays": "number", "in_front": "number"}

    async def run(self, text: str = "", image: str = "", sound: str = "", seconds: float = 5.0,
                  volume: float = 1.0, highlight: str = "", wait: bool = False,
                  message: str = "") -> dict[str, Any]:
        if not (str(text).strip() or str(image).strip() or str(sound).strip()):
            raise ValueError("an alert needs a text, a picture or a sound")
        alert = Alert(str(text), _path(image), _path(sound), float(seconds), float(volume), (str(highlight),),
                      str(message))
        return {"overlays": self._queue.overlays, "in_front": await self._queue.show(alert, to_bool(wait))}
