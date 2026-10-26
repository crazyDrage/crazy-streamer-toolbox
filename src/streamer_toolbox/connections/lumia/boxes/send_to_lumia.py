from typing import Any

from streamer_toolbox.connections.lumia.boxes.lumia_box import LumiaBox, Retrieve, Send, _named, _object


class SendToLumia(LumiaBox):
    name = "send"
    label = "Send to Lumia"
    help = "Sends any other kind of thing Lumia Stream knows (a studio scene, text to speech, ...)"
    hints = {"value": "What that kind wants: a scene's name, the text to speak, ...",
             "values": "Optional: more settings for it, as an object"}

    def __init__(self, send: Send, retrieve: Retrieve) -> None:
        super().__init__(send, retrieve)
        self.options = {"kind": self.kinds}

    async def run(self, kind: str, value: str = "", values: Any = None) -> None:
        await self._send({"type": _named(kind, "kind"), "params": {"value": value, **_object(values)}})
