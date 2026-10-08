from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.interfaces.confirm_service import ConfirmService
from streamer_toolbox.core.interfaces.message_service import MessageService

ANSWERS = {True: "yes", False: "no", None: "no_answer"}


class PopupActions:
    """Popups in the toolbox's own window (PC, phone, tablet): a message (SAMMI's popup message) and a yes/no
    question whose answer picks the way on."""

    def __init__(self, messages: MessageService, confirm: ConfirmService) -> None:
        self._messages = messages
        self._confirm = confirm

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("popup.message", self.message, "Shows a message on every open toolbox screen until OK is "
                    "pressed; the flow goes on right away", "Show message", group="Popups")
        actions.add("popup.ask", self.ask, "Asks a yes/no question on every open toolbox screen; the first answer "
                    "picks the way on. 'no_answer' if nobody answers in time or no toolbox screen is open",
                    "Ask yes/no", group="Popups", ports=tuple(ANSWERS.values()), flow_only=True)

    async def message(self, message: str, title: str = "") -> int:
        return await self._messages.show(str(message), str(title))

    async def ask(self, question: str, seconds: float = 20) -> str:
        return ANSWERS[await self._confirm.ask(str(question), float(seconds))]
