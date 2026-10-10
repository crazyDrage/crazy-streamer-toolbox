import logging
from typing import Optional

from nicegui import ui

from streamer_toolbox.gui.services.confirm_round import ConfirmRound
from streamer_toolbox.core.interfaces.confirm_service import ConfirmService
from streamer_toolbox.gui.services.open_pages import OpenPages

log = logging.getLogger(__name__)


class NiceGuiConfirmService(ConfirmService):
    """Shows the question as a dialog in every open toolbox page (PC, phone, tablet); first answer wins."""

    def __init__(self, pages: OpenPages) -> None:
        self._pages = pages

    async def ask(self, question: str, timeout: float = 20.0) -> Optional[bool]:
        clients = self._pages.clients()
        if not clients:
            log.info("no GUI open, cannot ask: %s", question)
            return None
        round_ = ConfirmRound()
        dialogs = []
        for client in clients:
            with client:
                # big targets: this gets answered mid-stream, often on a phone or tablet
                with ui.dialog().props("persistent") as dialog, ui.card().classes("w-[28rem] max-w-full p-6 gap-5"):
                    ui.label(question).classes("text-xl font-semibold")
                    with ui.row().classes("w-full no-wrap gap-3"):
                        ui.button("Yes", icon="check", on_click=lambda: round_.answer(True)) \
                            .props("color=positive unelevated no-caps size=lg").classes("flex-1 h-14")
                        ui.button("No", icon="close", on_click=lambda: round_.answer(False)) \
                            .props("color=negative unelevated no-caps size=lg").classes("flex-1 h-14")
                dialog.open()
            dialogs.append(dialog)
        try:
            return await round_.wait(timeout)
        finally:
            for dialog in dialogs:
                if not dialog.is_deleted:
                    dialog.delete()
