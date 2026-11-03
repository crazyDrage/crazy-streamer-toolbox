from abc import ABC, abstractmethod


class Tool(ABC):
    """A tool under Tools: a card on its overview, an item in the side menu and a page of its own.

    `build()` draws it with NiceGUI each time the page opens (once per browser tab): create the inputs inside
    it, not in __init__, since this one object is shared by every open page."""

    title: str = ""
    icon: str = "build"        # a Material icon name: fonts.google.com/icons
    description: str = ""      # its line on the Tools overview

    @abstractmethod
    def build(self) -> None:
        """Draws the tool (NiceGUI)."""
