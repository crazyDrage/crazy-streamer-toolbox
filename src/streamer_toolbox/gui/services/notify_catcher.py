import logging
from typing import Any

from nicegui import context, ui

from streamer_toolbox.gui.components.info_bar import InfoBar
from streamer_toolbox.gui.services.message_log import MessageLog

log = logging.getLogger(__name__)


class NotifyCatcher:
    """Every ui.notify of the toolbox and its plugins goes into the MessageLog and into the info bar of the page
    it was meant for (his round 81: the bar replaces the pop-ups), in one place, so no page has to change.

    A page without the bar (the Live buttons on their own, the test window) still gets the pop-up, and so does a
    message with buttons of its own (the Show message box's OK: it waits for him)."""

    def __init__(self, messages: MessageLog) -> None:
        self._messages = messages
        self._bars: dict[str, InfoBar] = {}
        self._pop_up = ui.notify

    def install(self) -> None:
        ui.notify = self.notify

    def attach(self, bar: InfoBar) -> None:
        """The page being built has this bar."""
        client = context.client
        self._bars[client.id] = bar
        client.on_delete(lambda: self._bars.pop(client.id, None))

    def notify(self, message: Any, **options: Any) -> None:
        caption = options.get("caption")
        text = str(message) + (f"\n{caption}" if caption else "")
        entry = self._messages.add(options.get("type") or "info", text)
        try:
            client = context.client
        except Exception:  # no page around it (a background task): the Debug list has it
            log.info("message: %s", text)
            return
        bar = self._bars.get(client.id)
        if bar is None or options.get("actions"):
            self._pop_up(message, **options)
            return
        bar.show(entry)
