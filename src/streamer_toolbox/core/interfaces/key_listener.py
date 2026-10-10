from abc import ABC, abstractmethod
from collections.abc import Callable


class KeyListener(ABC):
    """Listens to the keyboard of this PC (every window, not only the toolbox) and reports each key press by its
    name, e.g. "f23" or "ctrl+shift+k". Only listens: keys still reach the other programs."""

    @abstractmethod
    def start(self, on_key: Callable[[str], None]) -> None:
        """Start listening; on_key(name) may be called from another thread."""

    @abstractmethod
    def stop(self) -> None:
        ...
