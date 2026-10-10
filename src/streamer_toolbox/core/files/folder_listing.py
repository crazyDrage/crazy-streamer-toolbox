from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FolderListing:
    """What the file window shows for one folder: its sub folders and files by name (A-Z), the folder above
    (None at the top of a drive), and why it couldn't be read ("" if it could)."""

    folder: Path
    parent: Path | None
    folders: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    problem: str = ""
