from collections.abc import Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField

from .lamp_actions import LampActions
from .pretend_lamp import PretendLamp


class LampConnection(ConnectionBase):
    """The lamp's CONNECTION: what makes a program show up under Connections, with its own tab.

    A connection answers five questions for the toolbox:
      1. Who are you?                 `id`, `title`, `icon`
      2. What do you need to know?    `fields()`: the inputs on the tab
      3. Can you reach the program?   `test(settings)`: the Connect button
      4. Go / stop                    `start()` and `stop()`
      5. What can you do?             `add_actions(actions)`: its boxes

    ConnectionBase already does the bookkeeping: it keeps the settings, adds the on / off switch
    ("enabled", OFF by default: a connection never talks to anything until the streamer pressed Connect) and
    holds the status that the tab shows. The settings are saved in `config/toolbox.toml` under `[example]`."""

    id = "example"        # must be the plugin's id: it names the settings table and the boxes ("example.…")
    title = "Example lamp"
    icon = "lightbulb"    # any Material icon name: fonts.google.com/icons

    def __init__(self, lamp: PretendLamp, blinked: Callable[[dict[str, Any]], None]) -> None:
        # The first argument is the DEFAULT settings. What the streamer saved comes on top, by itself.
        super().__init__({"name": "Desk lamp"})
        self._lamp = lamp
        self._blinked = blinked

    def fields(self) -> list[SettingField]:
        # One SettingField per input: (key in the settings, label, hint=...). For a password or a token add
        # secret=True. Better still, keep a secret in its own file, as the built-in connections do.
        return [SettingField("name", "The lamp's name", hint="Any name. A real connection would ask for an "
                                                             "address here, like ws://localhost:1234")]

    def add_gui_settings(self) -> None:
        # Optional: anything else the tab should show under the fields, drawn with NiceGUI.
        ui.label("This is the example plugin's pretend lamp. Nothing real is switched. Its boxes are under "
                 "\"Example lamp\" in the Add box window, and its tool is on the Tools page.") \
            .classes("text-sm opacity-80")

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """The Connect button. It gets the settings as typed, BEFORE they are saved, and only looks: it must
        not change anything. Give back a status: CONNECTED (with a few facts to show) or ERROR (with why)."""
        name = str(settings.get("name") or "").strip()
        if not name:
            return ConnectionStatus(ConnectionState.ERROR, "The lamp needs a name")
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Lamp", name), ("Colour", self._lamp.color)))

    async def start(self) -> None:
        """Called when the toolbox starts (if switched on) and after Connect. It must never raise: when
        something goes wrong, the reason goes into the status, and the tab shows it."""
        status = await self.test(self._settings)
        if status.ok:
            self._lamp.switch(True)
        self._set_status(status)

    async def stop(self) -> None:
        """Called when it is switched off and when the toolbox closes. Let go of everything here."""
        self._lamp.switch(False)
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    def add_actions(self, actions: ActionRegistry) -> None:
        LampActions(self._lamp, self._need_on, self._blinked).add_to(actions)

    def _need_on(self) -> None:
        """Every box calls this first, so a switched-off lamp gives one clear message instead of a crash."""
        if not self._settings["enabled"]:
            raise NotConnectedError("The example lamp is switched off under Connections → Example lamp")
        if not self._status.ok:
            raise NotConnectedError(f"The example lamp is not connected ({self._status.detail or 'press Connect'})")
