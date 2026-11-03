from abc import ABC, abstractmethod

from streamer_toolbox.core.interfaces.import_target import ImportTarget


class Importer(ABC):
    """An importer on Overlay → Import: brings things over from another program or service (StreamElements is
    the toolbox's own; a plugin can add one for another, his round 64). `build(target)` draws its card with
    NiceGUI each time the page opens and hands what it brought to `target`."""

    title: str = ""
    icon: str = "file_download"  # a Material icon name: fonts.google.com/icons
    description: str = ""        # one line under its title

    @abstractmethod
    def build(self, target: ImportTarget) -> None:
        """Draws the importer's card (NiceGUI)."""
