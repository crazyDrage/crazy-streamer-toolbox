from collections.abc import Callable
from typing import Any

from streamer_toolbox.connections.keyboard.key_name import KeyName
from streamer_toolbox.core.interfaces.key_listener import KeyListener


class PynputKeyListener(KeyListener):
    """KeyListener with pynput (a system-wide hook in its own thread, no admin rights needed on Windows). It
    remembers which modifiers are held, so ctrl+shift+k arrives as one name."""

    def __init__(self) -> None:
        self._listener: Any = None
        self._held: set[str] = set()

    def start(self, on_key: Callable[[str], None]) -> None:
        from pynput import keyboard  # only here: tests and machines without it never import it

        self.stop()

        def pressed(key: Any) -> None:
            modifier = KeyName.modifier(key)
            if modifier:
                self._held.add(modifier)
            else:
                on_key(KeyName.of(key, self._held))

        def released(key: Any) -> None:
            self._held.discard(KeyName.modifier(key))

        self._listener = keyboard.Listener(on_press=pressed, on_release=released)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._held.clear()
