from streamer_toolbox.connections.mixitup.boxes.add_currency import AddCurrency
from streamer_toolbox.connections.mixitup.boxes.add_item import AddItem
from streamer_toolbox.connections.mixitup.boxes.add_to_counter import AddToCounter
from streamer_toolbox.connections.mixitup.boxes.clear_chat import ClearChat
from streamer_toolbox.connections.mixitup.boxes.command_on_off import CommandOnOff
from streamer_toolbox.connections.mixitup.boxes.get_counter import GetCounter
from streamer_toolbox.connections.mixitup.boxes.get_currency import GetCurrency
from streamer_toolbox.connections.mixitup.boxes.get_item import GetItem
from streamer_toolbox.connections.mixitup.boxes.get_viewer import GetViewer
from streamer_toolbox.connections.mixitup.boxes.mixitup_box import Send
from streamer_toolbox.connections.mixitup.boxes.reset_counter import ResetCounter
from streamer_toolbox.connections.mixitup.boxes.run_mix_it_up_command import RunMixItUpCommand
from streamer_toolbox.connections.mixitup.boxes.send_chat import SendChat
from streamer_toolbox.connections.mixitup.boxes.set_counter import SetCounter
from streamer_toolbox.connections.mixitup.boxes.set_currency import SetCurrency
from streamer_toolbox.connections.mixitup.boxes.set_item import SetItem
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class MixItUpActions:
    """Every part of Mix It Up's Developer API v2 as boxes (mixitup.bot/docs/reference/developer-api): commands
    (run, on / off), chat (send, clear), a viewer (by platform + name) and their currency (rats), inventory items,
    counters. Names in, IDs looked up: a renamed command or currency needs no change in the flow.

    One Box class per box, in boxes/."""

    def __init__(self, send: Send) -> None:
        self._send = send

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (RunMixItUpCommand(self._send), CommandOnOff(self._send), SendChat(self._send),
                    ClearChat(self._send), GetViewer(self._send), GetCurrency(self._send), AddCurrency(self._send),
                    SetCurrency(self._send), GetItem(self._send), AddItem(self._send), SetItem(self._send),
                    GetCounter(self._send), AddToCounter(self._send), SetCounter(self._send),
                    ResetCounter(self._send)):
            actions.add_box(box, "mixitup")
