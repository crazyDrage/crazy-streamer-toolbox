from streamer_toolbox.connections.firebot.boxes.firebot_box import Send
from streamer_toolbox.connections.firebot.boxes.get_firebot_counter import GetFirebotCounter
from streamer_toolbox.connections.firebot.boxes.get_firebot_variable import GetFirebotVariable
from streamer_toolbox.connections.firebot.boxes.run_firebot_effect_list import RunFirebotEffectList
from streamer_toolbox.connections.firebot.boxes.set_firebot_counter import SetFirebotCounter
from streamer_toolbox.connections.firebot.boxes.set_firebot_variable import SetFirebotVariable
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class FirebotActions:
    """Firebot's boxes, over its local API (docs.firebot.app/v5/dev/api). What happens is built in Firebot
    as a preset effect list; the toolbox runs it by name (the picker lists them from the running program)
    and can hand it arguments. Custom variables and counters can be read and set.

    One Box class per box, in boxes/."""

    def __init__(self, send: Send) -> None:
        self._send = send

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (RunFirebotEffectList(self._send), GetFirebotVariable(self._send),
                    SetFirebotVariable(self._send), GetFirebotCounter(self._send), SetFirebotCounter(self._send)):
            actions.add_box(box, "firebot")
