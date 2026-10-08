import secrets
from collections.abc import Callable
from pathlib import Path
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.voicemod.voicemod_actions import VoicemodActions
from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.connections.websocket.request_socket import RequestSocket
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.setting_field import SettingField

DOCS = "https://control-api.voicemod.net/"
PORTS = (59129, 20000, 39273, 42152, 43782, 46667, 35679, 37170, 38501, 33952, 30546)  # Voicemod's own list


class VoicemodConnection(LineConnection):
    """Voicemod (voice changer and soundboard), over its Control API: a websocket at `ws://localhost:<port>/v1`
    on one of the ports Voicemod names; they are tried in turn unless an address is typed. Its boxes are in
    VoicemodActions.

    Voicemod wants an API key from every program (asked for on control-api.voicemod.net, sent by mail); it is
    kept in its own file (config/voicemod_key.txt), never in toolbox.toml and never shown. Built from
    Voicemod's docs, never run against the real program. NOT CONFIRMED: under which name an answer carries
    its request's id (`id` and `actionID` are both taken), where an answer holds its content
    (`actionObject`, else `payload`), and the list's name in the sounds' answer (`listOfMemes`). Switching
    a voice or playing a sound doesn't wait for an answer.
    Off until switched on."""

    id = "voicemod"
    title = "Voicemod"
    icon = "record_voice_over"

    def __init__(self, settings: dict[str, Any], key_path: Path,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0,
                 ports: tuple[int, ...] = PORTS) -> None:
        self._key = SecretFile(key_path, "API key", "Voicemod sends it by mail, see the tab's link")
        self._ports = ports
        self._at = 0
        super().__init__({"url": ""}, settings, connect, retry_delay)

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address", hint="leave empty: Voicemod's ports are tried in turn. Else "
                                                    "like ws://localhost:59129/v1")]

    def add_gui_settings(self) -> None:
        ui.label(f"The API key is read from {self._key.path}: the key Voicemod mailed you, nothing else in "
                 "the file. Ask for one on Voicemod's page (free, a short form).").classes("text-sm opacity-80")
        ui.label("Not tried with the real program yet. Boxes: Set Voicemod voice, Random voice, Play / Stop "
                 "Voicemod sound, Flip Voicemod switch.").classes("text-xs opacity-60")
        ui.link("Voicemod's Control API page", DOCS, new_tab=True).classes("text-sm")

    def add_actions(self, actions: ActionRegistry) -> None:
        VoicemodActions(self._request).add_to(actions)

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Looks for Voicemod on each of its ports; the one that answers is used from then on."""
        try:
            self._key.read()
        except ValueError as e:
            return ConnectionStatus(ConnectionState.ERROR, str(e))
        if str(settings.get("url") or "").strip():
            return await super().test(settings)
        for at in range(len(self._ports)):
            self._at = at
            if (await super().test(settings)).ok:
                return ConnectionStatus(ConnectionState.CONNECTED, "", (("Port", str(self._ports[at])),))
        return ConnectionStatus(ConnectionState.ERROR, "can't find Voicemod on any of its ports: is it running?")

    def _url(self, settings: dict[str, Any]) -> str:
        self._key.read()  # nothing to connect for without the key
        return str(settings.get("url") or "").strip() or f"ws://localhost:{self._ports[self._at]}/v1"

    def _hide(self, text: str) -> str:
        return self._key.hide(text)

    def _facts(self) -> tuple[tuple[str, str], ...]:
        return (("Address", self._url(self._settings)),)

    def _state(self, text: str) -> None:
        if text != "connected":
            self._at = (self._at + 1) % len(self._ports)  # the next try looks on the next port
        super()._state(text)

    def _reply_id(self, message: dict[str, Any]) -> Any:
        return message.get("id") or message.get("actionID")

    async def _opened(self, line: RequestSocket) -> None:
        answer = await line.request({"action": "registerClient", "payload": {"clientKey": self._key.read()}})
        status = answer["payload"].get("status") if isinstance(answer.get("payload"), dict) else None
        if not isinstance(status, dict) or int(status.get("code") or 0) != 200:
            raise PermissionError("Voicemod refused the API key")

    async def _request(self, action: str, payload: dict[str, Any], answered: bool = True) -> dict[str, Any]:
        message: dict[str, Any] = {"action": action, "payload": payload}
        if not answered:  # Voicemod wants an id on every message, also on those it doesn't answer
            message["id"] = secrets.token_hex(6)
        answer = await self._ask(message, answered)
        content = answer.get("actionObject", answer.get("payload"))
        return content if isinstance(content, dict) else {}
