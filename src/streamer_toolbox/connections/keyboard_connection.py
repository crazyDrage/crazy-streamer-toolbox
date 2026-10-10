import asyncio
from collections.abc import Callable
from typing import Any

from streamer_toolbox.connections.keyboard.key_name import KeyName
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.interfaces.key_listener import KeyListener

KEY_PRESSED = "key.pressed"  # event: {key} when a key a flow listens for is pressed (e.g. F23 from a macro pad)


class KeyboardConnection(ConnectionBase):
    """Keyboard triggers, like SAMMI's keyboard buttons (F23 / F24 from a Stream Deck or macro pad): a key press
    anywhere on this PC starts the flows whose trigger names that key. Only keys a flow asks for become events;
    other key presses are dropped at once, and typed text is never shown or logged."""

    id = "keyboard"
    title = "Keyboard"
    icon = "keyboard"

    def __init__(self, settings: dict[str, Any], listener: KeyListener, events: EventBus,
                 wanted: Callable[[str], bool]) -> None:
        super().__init__({}, settings)
        self._listener = listener
        self._events = events
        self._wanted = wanted
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last = ""  # last special key (F-keys, media keys, shortcuts), to learn its name on the tab

    def fields(self) -> list[SettingField]:
        return []

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        try:
            self._listener.start(self._from_thread)
        except Exception as e:  # e.g. pynput missing
            self._set_status(ConnectionStatus(ConnectionState.ERROR, f"can't listen to the keyboard: {e}"))
            return
        self._show()

    async def stop(self) -> None:
        self._listener.stop()
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Keyboard", "this PC, every window"),))

    def add_actions(self, actions: ActionRegistry) -> None:
        """No actions: the keyboard only starts flows (trigger "Key")."""

    def _from_thread(self, name: str) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._pressed, name)

    def _pressed(self, name: str) -> None:
        if not KeyName.is_text(name):
            self._last = name
            self._show()
        if self._wanted(name):
            self._events.publish(KEY_PRESSED, {"key": name})

    def _show(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("Listening", "every window on this PC"),
            ("Last special key", self._last or "none yet: press an F-key or a shortcut to see its name"),
        )))
