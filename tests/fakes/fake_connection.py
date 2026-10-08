from typing import Any

from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.setting_field import SettingField


class FakeConnection(ConnectionBase):
    """A connection whose test/start succeed only when url == "good"."""

    id = "fake"
    title = "Fake"
    icon = "bug_report"

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        super().__init__({"url": "", "password": ""}, settings)
        self.calls: list[str] = []

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address"), SettingField("password", "Password", secret=True)]

    async def start(self) -> None:
        self.calls.append("start")
        self._set_status(self._result(self._settings))

    async def stop(self) -> None:
        self.calls.append("stop")
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        self.calls.append("test")
        return self._result(settings)

    @staticmethod
    def _result(settings: dict[str, Any]) -> ConnectionStatus:
        if settings["url"] == "good":
            return ConnectionStatus(ConnectionState.CONNECTED)
        return ConnectionStatus(ConnectionState.ERROR, "bad url")
