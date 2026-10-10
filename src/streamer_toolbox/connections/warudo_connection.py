from typing import Any

from nicegui import ui

from streamer_toolbox.connections.warudo.warudo_actions import WarudoActions
from streamer_toolbox.connections.websocket.socket_message_sender import SocketMessageSender
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.gui.components.outside_link import outside_link

DOCS = "https://docs.warudo.app/docs/blueprints/overview"


class WarudoConnection(ConnectionBase):
    """Warudo (3D VTubing program): named actions into its blueprints, over its websocket on port 19190. The
    toolbox only sends; nothing is kept open, each action is its own short visit. Its box is in WarudoActions
    (the message's shape is not confirmed with the real program yet). Off until switched on."""

    id = "warudo"
    title = "Warudo"
    icon = "view_in_ar"
    retry_when_down = True

    def __init__(self, settings: dict[str, Any], sender: SocketMessageSender | None = None) -> None:
        super().__init__({"url": "ws://localhost:19190"}, settings)
        self._sender = sender or SocketMessageSender()

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Websocket address", hint="Warudo listens on port 19190 while it runs")]

    def add_gui_settings(self) -> None:
        ui.label('What Warudo does with an action is built in Warudo: start a blueprint with an "On WebSocket '
                 'Action" node and give it an Action Name. A flow\'s "Send action to Warudo" box with the '
                 'same name runs it.').classes("text-sm opacity-80")
        ui.label("Not tried with the real program yet: the message's shape may still need a fix.") \
            .classes("text-xs opacity-60")
        outside_link("Warudo's handbook: blueprints", DOCS).classes("text-sm")

    async def start(self) -> None:
        self._set_status(await self.test(self._settings))

    async def stop(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Looks whether Warudo's websocket answers. Sends nothing."""
        try:
            await self._sender.send(str(settings["url"]))
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Websocket", str(settings["url"])),))

    def add_actions(self, actions: ActionRegistry) -> None:
        WarudoActions(self._send_text).add_to(actions)

    async def _send_text(self, text: str) -> None:
        if not self._settings["enabled"]:
            raise NotConnectedError("Warudo is switched off under Connections → Warudo")
        try:
            await self._sender.send(str(self._settings["url"]), text)
        except Exception as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))
            raise NotConnectedError(f"Warudo: {_reason(e)}") from None
        self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "",
                                          (("Websocket", str(self._settings["url"])),)))


def _reason(e: Exception) -> str:
    if isinstance(e, (OSError, TimeoutError)):
        return "can't reach Warudo: is it running?"
    return str(e) or type(e).__name__
