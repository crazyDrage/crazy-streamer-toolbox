import os
from pathlib import Path

from streamer_toolbox.core.files.file_types import FOLDER
from streamer_toolbox.core.files.folder_listing import FolderListing


class FileBrowser:
    """Looks around this PC's folders for the file window (a browser can't tell a page where a file really is, so
    the toolbox lists the folders itself; that also works from the tablet). Reads names only, never a file."""

    def __init__(self, home: Path | None = None) -> None:
        self._home = home or Path.home()

    def listing(self, folder: Path, endings: tuple[str, ...] = ()) -> FolderListing:
        """The folder's sub folders and its files with one of the endings (() = every file, FOLDER = none)."""
        parent = folder.parent if folder.parent != folder else None
        try:
            entries = sorted(folder.iterdir(), key=lambda p: p.name.casefold())
        except OSError as e:
            return FolderListing(folder, parent, problem=_problem(e))
        folders, files = [], []
        for entry in entries:
            try:
                is_folder = entry.is_dir()
            except OSError:  # a broken link, a drive that went away
                continue
            if is_folder:
                folders.append(entry.name)
            elif endings != FOLDER and (not endings or entry.suffix.casefold() in endings):
                files.append(entry.name)
        return FolderListing(folder, parent, tuple(folders), tuple(files))

    def start(self, value: str = "", last: Path | None = None) -> Path:
        """Where the window opens: the folder of the field's value, else the last one used, else the home folder."""
        text = str(value or "").strip()
        if text and "${" not in text:
            path = Path(text)
            for folder in (path, path.parent):
                if folder.is_absolute() and folder.is_dir():
                    return folder
        return last if last is not None and last.is_dir() else self._home

    def places(self) -> dict[str, str]:
        """Folder → name, to jump to: the home folder, its usual media folders, every drive."""
        places = {str(self._home): "Home"}
        for name in ("Videos", "Pictures", "Music", "Downloads", "Desktop", "Documents"):
            if (self._home / name).is_dir():
                places[str(self._home / name)] = name
        for drive in os.listdrives() if hasattr(os, "listdrives") else ("/",):
            places[drive] = drive
        return places


def _problem(error: OSError) -> str:
    if isinstance(error, PermissionError):  # an OSError too: checked first
        return "Windows doesn't let the toolbox look into this folder"
    if isinstance(error, FileNotFoundError):
        return "this folder isn't there"
    if isinstance(error, NotADirectoryError):
        return "this is a file, not a folder"
    return str(error)
