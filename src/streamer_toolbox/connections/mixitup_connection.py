from typing import Any

import httpx

from streamer_toolbox.connections.mixitup.mixitup_actions import MixItUpActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.web.web_client import web_client


class MixItUpConnection(ConnectionBase):
    """Mix It Up's Developer API (mixitup.bot/docs/reference/developer-api); its boxes are in MixItUpActions.
    Points (rats) stay in Mix It Up."""

    id = "mixitup"
    title = "Mix It Up"
    icon = "smart_toy"
    retry_when_down = True

    def __init__(self, settings: dict[str, Any], transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__({"url": "http://localhost:8911/api/v2"}, settings)
        self._transport = transport

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address", hint="Mix It Up → Services → Developer API must be on")]

    async def start(self) -> None:
        self._set_status(await self.test(self._settings))

    async def stop(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        try:
            version = await self._request(settings, "GET", "status/version")
            commands = await self._request(settings, "GET", "commands", params={"pageSize": 1})
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("Mix It Up", str(version)),
            ("Commands", str(commands.get("TotalCount", "?"))),
        ))

    def add_actions(self, actions: ActionRegistry) -> None:
        MixItUpActions(self._send).add_to(actions)

    async def send(self, method: str, path: str, **kwargs: Any) -> Any:
        """Any call of Mix It Up's Developer API, for parts of the toolbox that aren't its boxes (the points'
        MixItUpPointBank). Switched off or not reachable raises, as the boxes do."""
        return await self._send(method, path, **kwargs)

    async def _send(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self._settings["enabled"]:
            raise NotConnectedError("Mix It Up is switched off under Connections → Mix It Up")
        try:
            result = await self._request(self._settings, method, path, **kwargs)
        except httpx.HTTPStatusError as e:  # Mix It Up answered: the connection is fine, this request wasn't
            raise RuntimeError(f"Mix It Up: {_answer(e.response)}") from None
        except Exception as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))
            raise
        if not self.status.ok:
            await self.start()
        return result

    async def _request(self, settings: dict[str, Any], method: str, path: str, **kwargs: Any) -> Any:
        async with web_client(self._transport, timeout=5) as client:
            response = await client.request(method, settings["url"].rstrip("/") + "/" + path, **kwargs)
        response.raise_for_status()
        if not response.content:
            return None
        if "json" in response.headers.get("content-type", ""):
            return response.json()
        return response.text  # e.g. /status/version answers text/plain


def _reason(e: Exception) -> str:
    if isinstance(e, httpx.ConnectError):
        return "can't reach Mix It Up: is it running, with the Developer API on?"
    return str(e) or type(e).__name__


def _answer(response: httpx.Response) -> str:
    """Mix It Up's own words for a refused request ({"title", "detail"}, e.g. "User 'x' not found on platform
    'Twitch'"), else the status."""
    try:
        problem = response.json()
    except ValueError:
        problem = {}
    if isinstance(problem, dict) and (problem.get("detail") or problem.get("title")):
        return str(problem.get("detail") or problem.get("title"))
    return f"{response.status_code} {response.reason_phrase}".strip()
