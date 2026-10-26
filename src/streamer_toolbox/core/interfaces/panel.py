from abc import ABC, abstractmethod


class Panel(ABC):
    """A card in one of the toolbox's areas: `section` "connections" (on Connections), "live" or "settings"
    (both under Plugins → the plugin). `build()` draws it with NiceGUI each time it is shown."""

    title: str = ""
    section: str = "live"

    @abstractmethod
    def build(self) -> None:
        """Draws the card (NiceGUI)."""
