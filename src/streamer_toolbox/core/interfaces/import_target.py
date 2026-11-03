from abc import ABC, abstractmethod

from streamer_toolbox.core.widgets.widget import Widget


class ImportTarget(ABC):
    """Where an importer hands over what it brought (Overlay → Import). Widgets for now; more kinds can follow
    (flows from another program, ...)."""

    @abstractmethod
    def widget_names(self) -> list[str]:
        """The widgets there are, so an importer can tell what is new."""

    @abstractmethod
    def add_widget(self, widget: Widget, files: dict[str, bytes] | None = None) -> str:
        """Saves a widget, with files for its media folder (file name → content). A name that is taken gets a
        number (chat_box_2). Gives the name it was saved under; the Widgets list shows it."""
