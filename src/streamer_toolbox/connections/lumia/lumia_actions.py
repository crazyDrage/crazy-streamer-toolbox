from streamer_toolbox.connections.lumia.boxes.fire_lumia_alert import FireLumiaAlert
from streamer_toolbox.connections.lumia.boxes.lumia_box import Retrieve, Send
from streamer_toolbox.connections.lumia.boxes.run_lumia_command import RunLumiaCommand
from streamer_toolbox.connections.lumia.boxes.send_to_lumia import SendToLumia
from streamer_toolbox.connections.lumia.boxes.set_lumia_lights import SetLumiaLights
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class LumiaActions:
    """Lumia Stream's boxes, all through its Send API (dev.lumiastream.com): run one of its commands or
    alerts by name (the pickers list them from the running program), or set the lights to a colour.
    "Send to Lumia" is for the kinds without a box of their own (studio-scene, tts, ...): Lumia's docs name
    the kind and a value, which is what it sends.

    One Box class per box, in boxes/."""

    def __init__(self, send: Send, retrieve: Retrieve) -> None:
        self._send = send
        self._retrieve = retrieve

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (RunLumiaCommand(self._send, self._retrieve), FireLumiaAlert(self._send, self._retrieve),
                    SetLumiaLights(self._send, self._retrieve), SendToLumia(self._send, self._retrieve)):
            actions.add_box(box, "lumia")
