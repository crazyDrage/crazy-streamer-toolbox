from typing import Any

from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.setting_field import SettingField


class FakeLineConnection(LineConnection):
    """A LineConnection to a local test server at `url`; its requests carry their id under "ref". `states`
    keeps every status it was given."""

    id = "fake_line"
    title = "Fake"
    icon = "cable"
    id_key = "ref"

    def __init__(self, url: str, retry_delay: float = 5.0) -> None:
        self.states: list[ConnectionState] = []
        super().__init__({"url": ""}, {"enabled": True, "url": url}, retry_delay=retry_delay, again_after=0.01)

    def fields(self) -> list[SettingField]:
        return []

    def add_actions(self, actions: ActionRegistry) -> None:
        pass

    def _url(self, settings: dict[str, Any]) -> str:
        return str(settings["url"])

    async def ask(self, message: dict[str, Any]) -> dict[str, Any]:
        return await self._ask(message)

    def _set_status(self, status: ConnectionStatus) -> None:
        self.states.append(status.state)
        super()._set_status(status)
