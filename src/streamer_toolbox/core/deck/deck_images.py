import re
from pathlib import Path, PureWindowsPath

KINDS = (".png", ".jpg", ".jpeg", ".gif", ".webp")  # pictures a browser shows; no .svg (it can carry a script)
URL = "/deck-images"  # where the toolbox serves the folder


class DeckImages:
    """The pictures on Live deck buttons: files in one folder of the toolbox's own data (config/deck_images),
    added through the button's window. A button keeps the file's name."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def add(self, name: str, content: bytes) -> str:
        """Keeps a picture and gives the name it has in the folder: the same file again keeps its name, another
        file with a taken name gets a number."""
        # PureWindowsPath: a name from a Windows browser may carry its folder with \ also on Linux
        path = Path(re.sub(r"[^A-Za-z0-9._-]+", "_", PureWindowsPath(name).name).strip("._") or "picture")
        if path.suffix.lower() not in KINDS:
            raise ValueError(f"A picture has to be one of {', '.join(KINDS)}")
        self.folder.mkdir(parents=True, exist_ok=True)
        stem, suffix, number = path.stem, path.suffix.lower(), 1
        target = self.folder / f"{stem}{suffix}"
        while target.is_file() and target.read_bytes() != content:
            number += 1
            target = self.folder / f"{stem}_{number}{suffix}"
        target.write_bytes(content)
        return target.name

    @staticmethod
    def url(name: str) -> str:
        return f"{URL}/{name}" if name else ""
