from collections.abc import Callable

from streamer_toolbox.core.interfaces.key_listener import KeyListener


class FakeKeyListener(KeyListener):
    """Presses keys by name from a test (as if from pynput's thread)."""

    def __init__(self) -> None:
        self.on_key: Callable[[str], None] | None = None
        self.stopped = False

    def start(self, on_key: Callable[[str], None]) -> None:
        self.on_key = on_key

    def stop(self) -> None:
        self.stopped = True

    def press(self, name: str) -> None:
        self.on_key(name)
