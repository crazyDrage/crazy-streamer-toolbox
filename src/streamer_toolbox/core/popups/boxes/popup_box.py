from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.interfaces.confirm_service import ConfirmService
from streamer_toolbox.core.interfaces.message_service import MessageService

ANSWERS = {True: "yes", False: "no", None: "no_answer"}


class PopupBox(Box):
    """What the popup boxes share (not a box itself: it has no run).

    Popups in the toolbox's own window (PC, phone, tablet): a message (SAMMI's popup message) and a yes/no
    question whose answer picks the way on."""

    def __init__(self, messages: MessageService, confirm: ConfirmService) -> None:
        self._messages = messages
        self._confirm = confirm
