import re
from pathlib import Path

from streamer_toolbox.core.widgets.element_design import ENDINGS

VALUE = re.compile(r"\{[\w-]+\}")
# what a value may be in a path: no folder in it, no way up
ONE_NAME = r"(?:(?!\.\.)[^/\\])*"
SHOWN = tuple(ending for ending, mime in ENDINGS.items() if mime.startswith(("image/", "video/")))


class EntryFiles:
    """The files on this PC an event list's picture and video cells show (his round 89 check: "a URL or local
    file path, or just a path in the toolbox's folder", with the event's values in it). The widget page asks
    for the path as it filled it in; it gets the file only when the path is one of the widget's own addresses
    with values in it (a value is never a folder or a way up), and only a picture or a video. A path that isn't
    a whole one is in the toolbox's folder."""

    def __init__(self, toolbox_folder: Path) -> None:
        self._toolbox_folder = toolbox_folder

    def find(self, addresses: set[str], wanted: str) -> Path | None:
        wanted = wanted.strip()
        if not wanted or not any(_pattern(address).fullmatch(wanted) for address in addresses):
            return None
        path = Path(wanted)
        if not path.is_absolute():
            path = self._toolbox_folder / path
        if path.suffix.casefold() not in SHOWN or not path.is_file():
            return None
        return path


def _pattern(address: str) -> re.Pattern[str]:
    parts = VALUE.split(address.strip())
    return re.compile(ONE_NAME.join(re.escape(part) for part in parts))
