from typing import Any

import httpx
from nicegui import ui

from streamer_toolbox.connections.firebot.firebot_actions import FirebotActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.gui.components.outside_link import outside_link

DOCS = "https://docs.firebot.app/v5/dev/api"


class FirebotConnection(ConnectionBase):
    """Firebot's local API on port 7472 (docs.firebot.app/v5/dev/api); its boxes are in FirebotActions.
    No login. The toolbox only sends: Firebot also has a websocket that tells its events, but its docs don't
    show what an event looks like, so nothing listens to it yet. Built from Firebot's docs. Tried on the
    real program (2026-10-11): the connection and the two variable boxes; no effect list and no counter
    existed there, so those boxes only showed their "Firebot has no ... named" answer. Off until switched on."""

    id = "firebot"
    title = "Firebot"
    icon = "local_fire_department"
    retry_when_down = True

    def __init__(self, settings: dict[str, Any], transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__({"url": "http://localhost:7472/api/v1"}, settings)
        self._transport = transport

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address", hint="Firebot must be running; its API is on by itself")]

    def add_gui_settings(self) -> None:
        ui.label("Boxes: Run Firebot effect list (picked from a list), "
                 "Firebot variables and counters. What happens is built in Firebot as a preset effect list.") \
            .classes("text-sm opacity-80")
        outside_link("Firebot's page about its API", DOCS).classes("text-sm")

    async def start(self) -> None:
        self._set_status(await self.test(self._settings))

    async def stop(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Asks for the preset effect lists: says whether Firebot is there. Changes nothing."""
        try:
            presets = await self._request(settings, "GET", "effects/preset")
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("Preset effect lists", str(len(presets) if isinstance(presets, list) else "?")),))

    def add_actions(self, actions: ActionRegistry) -> None:
        FirebotActions(self._send).add_to(actions)

    async def _send(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self._settings["enabled"]:
            raise NotConnectedError("Firebot is switched off under Connections → Firebot")
        try:
            result = await self._request(self._settings, method, path, **kwargs)
        except httpx.HTTPStatusError as e:  # Firebot answered: the connection is fine, this request wasn't
            raise RuntimeError(f"Firebot: {_answer(e.response)}") from None
        except Exception as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))
            raise NotConnectedError(f"Firebot: {_reason(e)}") from None
        if not self.status.ok:
            await self.start()
        return result

    async def _request(self, settings: dict[str, Any], method: str, path: str, **kwargs: Any) -> Any:
        async with web_client(self._transport, timeout=5) as client:
            response = await client.request(method, str(settings["url"]).rstrip("/") + "/" + path, **kwargs)
        response.raise_for_status()
        if not response.content:
            return None
        return response.json() if "json" in response.headers.get("content-type", "") else response.text


def _reason(e: Exception) -> str:
    if isinstance(e, httpx.ConnectError):
        return "can't reach Firebot: is it running?"
    return str(e) or type(e).__name__


def _answer(response: httpx.Response) -> str:
    try:
        problem = response.json()
    except ValueError:
        problem = {}
    if isinstance(problem, dict) and (problem.get("message") or problem.get("error")):
        return str(problem.get("message") or problem.get("error"))
    return f"{response.status_code} {response.reason_phrase}".strip()
