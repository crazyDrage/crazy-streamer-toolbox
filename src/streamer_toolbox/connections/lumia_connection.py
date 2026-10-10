from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import websockets
from nicegui import ui

from streamer_toolbox.connections.lumia.lumia_actions import LumiaActions
from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.gui.components.outside_link import outside_link
from streamer_toolbox.gui.components.secret_input import SecretInput

DOCS = "https://dev.lumiastream.com/docs/intro"
EVENT = "lumia.event"


class LumiaConnection(LineConnection):
    """Lumia Stream (smart lights and more), over its developer API on port 39231: boxes run its commands
    and alerts and set the lights (LumiaActions, its Send API), and what Lumia sees comes in as
    `lumia.event` (trigger "Lumia event", by type: chat, command, alert, ...) over its websocket.

    The token is from Lumia's settings and lets a program steer it: kept in its own file
    (config/lumia_token.txt), never in toolbox.toml and never shown. Lumia wants it in the address, so no
    address is ever put into an error text. Built from Lumia's docs. Tried on the real program
    (2026-10-10, no lamp linked): it connects, the pickers fill, Lumia takes an alert, a colour and a studio
    animation, and refuses a command that is switched off there in its own words. No event was seen coming in.
    NOT CONFIRMED: where an event's data holds the viewer's name and message (`username`, `message` are
    looked for). Off until switched on."""

    id = "lumia"
    title = "Lumia Stream"
    icon = "lightbulb"

    def __init__(self, settings: dict[str, Any], token_path: Path, events: EventBus,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._token = SecretFile(token_path, "token", "Lumia Stream → Settings → API")
        self._events = events
        self._transport = transport
        super().__init__({"url": "http://localhost:39231"}, settings, connect, retry_delay)

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address", hint="Lumia Stream → Settings → API: the developer API on")]

    def add_gui_settings(self) -> None:
        SecretInput(self._token, "Token")
        ui.label("The token: from Lumia Stream → Settings → API.").classes("text-sm opacity-80")
        ui.label("Its trigger was not seen with the real program yet. Boxes: Run Lumia command, Fire Lumia "
                 "alert, Set Lumia lights, Send to Lumia. Trigger: \"Lumia event\".").classes("text-xs opacity-60")
        outside_link("Lumia Stream's developer pages", DOCS).classes("text-sm")

    def add_actions(self, actions: ActionRegistry) -> None:
        LumiaActions(self._send, self._retrieve).add_to(actions)

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Asks Lumia for its settings once: says whether it is there and takes the token."""
        try:
            data = await self._call(settings, "GET", "retrieve", params={"slim": "true"})
        except (ValueError, ConnectionError, RuntimeError) as e:
            return ConnectionStatus(ConnectionState.ERROR, str(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Lights", str(len(data.get("lights") or []))),))

    def _url(self, settings: dict[str, Any]) -> str:
        base = str(settings["url"]).strip().rstrip("/")
        return "ws" + base.removeprefix("http") + "/api?token=" + self._token.read()

    def _hide(self, text: str) -> str:
        return self._token.hide(text)

    async def _message(self, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if not isinstance(kind, str) or str(message.get("event") or "").startswith("socketapi:"):
            return
        data = message.get("data") if isinstance(message.get("data"), dict) else {}
        self._events.publish(EVENT, {
            "type": kind, "alert": str(message.get("event") or "") if kind == "alert" else "",
            "origin": str(message.get("origin") or ""), "user": str(data.get("username") or ""),
            "message": str(data.get("message") or ""), "data": data})

    async def _send(self, body: dict[str, Any]) -> None:
        await self._on_call("POST", "send", json=body)

    async def _retrieve(self) -> dict[str, Any]:
        return await self._on_call("GET", "retrieve", params={"slim": "true"})

    async def _on_call(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self._settings["enabled"]:
            raise NotConnectedError("Lumia Stream is switched off under Connections → Lumia Stream")
        try:
            return await self._call(self._settings, method, path, **kwargs)
        except ValueError as e:
            raise NotConnectedError(str(e)) from None

    async def _call(self, settings: dict[str, Any], method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """One call of Lumia's API; its `data` (or {}). ValueError without a token, NotConnectedError when
        Lumia doesn't answer, RuntimeError with Lumia's words when it refuses."""
        params = {**kwargs.pop("params", {}), "token": self._token.read()}
        url = f"{str(settings['url']).strip().rstrip('/')}/api/{path}"
        try:
            async with web_client(self._transport, timeout=5) as client:
                response = await client.request(method, url, params=params, **kwargs)
        except httpx.HTTPError as e:  # its text would name the address, which holds the token
            raise NotConnectedError(f"can't reach Lumia Stream ({type(e).__name__}): is it running, with "
                                    "its API on?") from None
        try:
            answer = response.json()
        except ValueError:
            answer = {}
        answer = answer if isinstance(answer, dict) else {}
        if response.status_code >= 400 or answer.get("error"):
            reason = answer.get("error") or answer.get("message") or response.status_code
            raise RuntimeError(self._hide(f"Lumia Stream: {reason}"))
        return answer["data"] if isinstance(answer.get("data"), dict) else {}
