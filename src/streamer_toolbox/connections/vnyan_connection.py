from typing import Any

import httpx
from nicegui import ui

from streamer_toolbox.connections.vnyan.vnyan_actions import VNyanActions
from streamer_toolbox.connections.websocket.socket_message_sender import SocketMessageSender
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.gui.components.outside_link import outside_link

DOCS = "https://github.com/Suvidriel/VNyanDoc/wiki"


class VNyanConnection(ConnectionBase):
    """VNyan (3D VTubing program): named messages into its node graph, over its websocket receiver
    (Settings → Misc → WebSockets, "Start Receiver") and its web API on port 8069. The toolbox only sends;
    nothing is kept open, each message is its own short visit. Its boxes are in VNyanActions.
    Off until switched on."""

    id = "vnyan"
    title = "VNyan"
    icon = "pets"
    retry_when_down = True

    def __init__(self, settings: dict[str, Any], sender: SocketMessageSender | None = None,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__({"url": "ws://localhost:8000/vnyan", "api": "http://localhost:8069"},
                         settings)
        self._sender = sender or SocketMessageSender()
        self._transport = transport

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Websocket address",
                             hint="VNyan → Settings → Misc → WebSockets: Start Receiver on; the port is there"),
                SettingField("api", "API address", hint="for the Send API message box; VNyan listens on 8069")]

    def add_gui_settings(self) -> None:
        ui.label('What VNyan does with a message is built in VNyan: add a "WebSocket" node (or an "API '
                 'Message" node) to a node graph and give it a name. A flow\'s "Send message to VNyan" box '
                 'with the same name runs it.').classes("text-sm opacity-80")
        outside_link("VNyan's documentation", DOCS).classes("text-sm")

    async def start(self) -> None:
        self._set_status(await self.test(self._settings))

    async def stop(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Looks whether VNyan's websocket answers. Sends nothing."""
        try:
            await self._sender.send(str(settings["url"]))
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Websocket", str(settings["url"])),))

    def add_actions(self, actions: ActionRegistry) -> None:
        VNyanActions(self._send_text, self._send_api).add_to(actions)

    async def _send_text(self, text: str) -> None:
        self._need_switched_on()
        try:
            await self._sender.send(str(self._settings["url"]), text)
        except Exception as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))
            raise NotConnectedError(f"VNyan: {_reason(e)}") from None
        self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "",
                                          (("Websocket", str(self._settings["url"])),)))

    async def _send_api(self, body: dict[str, Any]) -> None:
        self._need_switched_on()
        try:
            async with web_client(self._transport, timeout=5) as client:
                response = await client.post(str(self._settings["api"]), json=body)
        except httpx.HTTPError as e:
            raise NotConnectedError(f"VNyan's API at {self._settings['api']} doesn't answer "
                                    f"({str(e) or type(e).__name__}): is VNyan running?") from None
        if response.status_code >= 400:
            raise RuntimeError(f"VNyan's API said {response.status_code} {response.reason_phrase}".strip())

    def _need_switched_on(self) -> None:
        if not self._settings["enabled"]:
            raise NotConnectedError("VNyan is switched off under Connections → VNyan")


def _reason(e: Exception) -> str:
    if isinstance(e, (OSError, TimeoutError)):
        return "can't reach VNyan: is it running, with Settings → Misc → WebSockets → Start Receiver on?"
    return str(e) or type(e).__name__
