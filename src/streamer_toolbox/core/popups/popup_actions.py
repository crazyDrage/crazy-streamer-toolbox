from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.interfaces.confirm_service import ConfirmService
from streamer_toolbox.core.interfaces.message_service import MessageService
from streamer_toolbox.core.popups.boxes.ask_yes_no import AskYesNo
from streamer_toolbox.core.popups.boxes.show_message import ShowMessage


class PopupActions:
    """Popups in the toolbox's own window (PC, phone, tablet): a message (SAMMI's popup message) and a yes/no
    question whose answer picks the way on.

    One Box class per box, in boxes/."""

    def __init__(self, messages: MessageService, confirm: ConfirmService) -> None:
        self._messages = messages
        self._confirm = confirm

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (ShowMessage(self._messages, self._confirm), AskYesNo(self._messages, self._confirm)):
            actions.add_box(box, "popup")
