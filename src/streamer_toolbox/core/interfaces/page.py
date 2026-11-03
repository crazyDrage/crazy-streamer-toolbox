from abc import ABC, abstractmethod


class Page(ABC):
    """A page of the plugin's own at /plugins/<id> (or /plugins/<id>/<subpath>). The one without a subpath is
    listed in the side list of the Plugins tab. `build()` draws it with NiceGUI each time it opens."""

    title: str = ""
    icon: str = "extension"    # a Material icon name
    subpath: str = ""

    @abstractmethod
    def build(self) -> None:
        """Draws the page (NiceGUI)."""
