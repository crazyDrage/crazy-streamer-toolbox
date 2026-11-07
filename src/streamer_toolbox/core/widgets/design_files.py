import re
from pathlib import PurePath

from streamer_toolbox.core.widgets.widget_store import WidgetStore

UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


class DesignFiles:
    """Puts a picture, GIF, video or sound he picked for the widget editor into the widget's media folder, under
    a name the folder takes (letters, digits, _ . -). The same file again is used again; another file with the
    same name gets a number."""

    def __init__(self, store: WidgetStore) -> None:
        self._store = store

    def add(self, widget: str, file_name: str, content: bytes) -> str:
        """The file's name in the media folder."""
        path = PurePath(file_name)
        stem = UNSAFE.sub("_", path.stem).strip("_.-") or "file"
        ending = UNSAFE.sub("", path.suffix.casefold())
        name, number = f"{stem}{ending}", 2
        while (there := self._store.media_file(widget, name)) is not None:
            if there.read_bytes() == content:
                return name
            name, number = f"{stem}_{number}{ending}", number + 1
        self._store.save_media(widget, name, content)
        return name
