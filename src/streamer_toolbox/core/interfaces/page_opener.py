from abc import ABC, abstractmethod


class PageOpener(ABC):
    """Shows the dashboard to the streamer once the server is up (browser tab, app window, ...)."""

    @abstractmethod
    def open(self, url: str) -> None:
        """Opens url; must not block."""
