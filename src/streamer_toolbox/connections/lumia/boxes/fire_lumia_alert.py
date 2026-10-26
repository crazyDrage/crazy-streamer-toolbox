from typing import Any

from streamer_toolbox.connections.lumia.boxes.lumia_box import LumiaBox, Retrieve, Send, _named, _object


class FireLumiaAlert(LumiaBox):
    name = "alert"
    label = "Fire Lumia alert"
    help = "Fires one of Lumia Stream's alerts"
    hints = {"values": 'Optional: what the alert may show, like {"username": "ann", "bits": 100}'}

    def __init__(self, send: Send, retrieve: Retrieve) -> None:
        super().__init__(send, retrieve)
        self.options = {"alert": self.alert_names}

    async def run(self, alert: str, values: Any = None) -> None:
        params: dict[str, Any] = {"value": _named(alert, "alert")}
        if _object(values):
            params["extraSettings"] = _object(values)
        await self._send({"type": "alert", "params": params})
