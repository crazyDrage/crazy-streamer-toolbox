import logging

from nicegui import ui

from streamer_toolbox.core.interfaces.message_service import MessageService
from streamer_toolbox.gui.services.open_pages import OpenPages

log = logging.getLogger(__name__)


class NiceGuiMessageService(MessageService):
    """Shows the message as a notification bar on every open toolbox page; it stays until OK is pressed."""

    def __init__(self, pages: OpenPages) -> None:
        self._pages = pages

    async def show(self, message: str, title: str = "") -> int:
        clients = self._pages.clients()
        if not clients:
            log.info("no GUI open, cannot show: %s", message)
        for client in clients:
            with client:
                # a Quasar action without a handler closes the notification
                ui.notify(title or message, caption=message if title else None, timeout=0, position="top",
                          multi_line=True, color="primary", textColor="white", icon="campaign",
                          actions=[{"label": "OK", "color": "white", "unelevated": True, "outline": True}])
        return len(clients)
