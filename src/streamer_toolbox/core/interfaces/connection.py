from abc import ABC, abstractmethod
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.interfaces.box import Box


class Connection(ABC):
    """A service the toolbox talks to (OBS, SAMMI, Mix It Up, Twitch...). Each gets its own tab under Connections.

    Settings live in the [<id>] table of toolbox.toml. "enabled" is always one of them and defaults to false:
    a connection is off until the streamer presses Connect or switches it on; enabled connections start when
    the toolbox starts.
    """

    id: str      # toml table name and tab id, e.g. "obs"
    title: str   # tab text
    icon: str    # Material icon name

    @abstractmethod
    def fields(self) -> list[SettingField]:
        """The inputs its tab shows (besides the on/off switch)."""

    @property
    @abstractmethod
    def settings(self) -> dict[str, Any]:
        """Current settings, including "enabled"."""

    @abstractmethod
    def configure(self, settings: dict[str, Any]) -> None:
        """Take new settings. Doesn't connect; the manager calls stop/start around it."""

    @property
    @abstractmethod
    def status(self) -> ConnectionStatus:
        ...

    @abstractmethod
    async def start(self) -> None:
        """Connect with the current settings. Never raises: a failure ends up in status."""

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Try these settings without keeping the connection or changing the current one. Read-only."""

    async def keep_alive(self) -> None:
        """Called every few seconds while switched on: connect again if the service came (back) up. Never raises."""

    def boxes(self) -> list[Box]:
        """Its boxes, one Box class each (they fail with a clear error while it's not connected). Their names
        get the connection's id in front ("set_color" → "example.set_color")."""
        return []

    def add_actions(self, actions: ActionRegistry) -> None:
        """The older way to give its boxes: register them on the registry yourself (the built-in connections
        still do). New code gives them through boxes()."""

    def add_gui_settings(self) -> None:
        """Extra NiceGUI content under the standard fields on its tab (e.g. OBS fit targets, the SAMMI deck)."""
