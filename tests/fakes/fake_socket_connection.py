from typing import Any

from streamer_toolbox.connections.websocket.socket_connection import SocketConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField


class FakeSocketConnection(SocketConnection):
    """A SocketConnection whose program fails the first `fails` sends. `restarts` counts restarts, `states`
    every status it was given, `sent` what got through."""

    id = "fake_socket"
    title = "Fake"
    icon = "cable"

    def __init__(self, fails: int, enabled: bool = True) -> None:
        super().__init__({}, {"enabled": enabled})
        self.fails = fails
        self.tries = 0
        self.restarts = 0
        self.sent: list[str] = []
        self.states: list[ConnectionState] = []

    def fields(self) -> list[SettingField]:
        return []

    def add_actions(self, actions: ActionRegistry) -> None:
        pass

    async def start(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.CONNECTED))

    async def stop(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        return ConnectionStatus(ConnectionState.CONNECTED)

    async def send(self, text: str) -> str:
        async def once() -> str:
            self.tries += 1
            if self.tries <= self.fails:
                raise ConnectionError("gone")
            self.sent.append(text)
            return text
        return await self._send_safely(once)

    def _set_status(self, status: ConnectionStatus) -> None:
        self.states.append(status.state)
        super()._set_status(status)

    async def _restart(self) -> None:
        self.restarts += 1

    def _lost(self, e: BaseException) -> NotConnectedError:
        self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))
        return NotConnectedError(f"Fake: {e}")
