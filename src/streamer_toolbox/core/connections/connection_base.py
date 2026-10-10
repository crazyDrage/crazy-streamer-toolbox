from typing import Any

from streamer_toolbox.core.interfaces.connection import Connection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError


class ConnectionBase(Connection):
    """Settings and status bookkeeping shared by the connections; subclasses do the talking."""

    retry_when_down = False  # True: keep_alive runs start() again while the last try failed

    async def keep_alive(self) -> None:
        if self.retry_when_down and self._settings["enabled"] and self._status.state is ConnectionState.ERROR:
            await self.start()

    def __init__(self, defaults: dict[str, Any], settings: dict[str, Any] | None = None) -> None:
        self._defaults = {"enabled": False, **defaults}
        self._settings = dict(self._defaults)
        self._status = ConnectionStatus(ConnectionState.OFF)
        self.configure(settings or {})

    @property
    def settings(self) -> dict[str, Any]:
        return dict(self._settings)

    def configure(self, settings: dict[str, Any]) -> None:
        self._settings = {**self._defaults, **{k: v for k, v in settings.items() if k in self._defaults}}
        if not self._settings["enabled"]:
            self._status = ConnectionStatus(ConnectionState.OFF)

    @property
    def status(self) -> ConnectionStatus:
        return self._status

    def _set_status(self, status: ConnectionStatus) -> None:
        self._status = status

    def _require_connected(self) -> None:
        if not self._status.ok:
            raise NotConnectedError(f"{self.title} is not connected ({self._status.detail or self._status.state.value})")
