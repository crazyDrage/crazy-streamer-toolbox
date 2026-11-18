import os
import sys
from pathlib import Path

from streamer_toolbox.core.fonts.font_face import FontFace
from streamer_toolbox.core.fonts.font_reader import FontReader
from streamer_toolbox.core.fonts.windows_font_names import WINDOWS_FONTS

FILE_KINDS = (".ttf", ".otf", ".ttc")
COPYABLE = (".ttf", ".otf")  # a browser can't load a .ttc collection from a web address


class InstalledFonts:
    """The fonts installed on this PC, for Settings → Fonts → Add font → From this PC (his 11-18). Windows: the
    system font folder and the per-user one (fonts installed "for me"); Linux: the usual font folders. Read
    when asked (a few hundred files), not at start.

    Which may be copied into the toolbox (all devices): none that come with Windows (Microsoft's list, or a
    "Microsoft" license / copyright text: those may only be used by name on this PC, temp/research/21), none
    whose file forbids embedding, and no .ttc (a browser can't load one). He still has to make sure the
    others' licenses allow it: the window says so."""

    def __init__(self, folders: list[Path] | None = None, reader: FontReader | None = None) -> None:
        self._folders = folders if folders is not None else self.default_folders()
        self._reader = reader or FontReader()

    @staticmethod
    def default_folders() -> list[Path]:
        if sys.platform == "win32":
            folders = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"]
            if os.environ.get("LOCALAPPDATA"):
                folders.append(Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts")
            return folders
        home = Path.home()
        return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), home / ".local" / "share" / "fonts",
                home / ".fonts"]

    def families(self) -> dict[str, list[FontFace]]:
        """Family → its faces, sorted by name."""
        found: dict[str, list[FontFace]] = {}
        for folder in self._folders:
            if not folder.is_dir():
                continue
            for path in sorted(folder.rglob("*")):
                if path.suffix.casefold() in FILE_KINDS and path.is_file():
                    for face in self._reader.read(path):
                        found.setdefault(face.family, []).append(face)
        return dict(sorted(found.items(), key=lambda item: item[0].casefold()))

    @staticmethod
    def comes_with_windows(face: FontFace) -> bool:
        if face.family.casefold() in WINDOWS_FONTS:
            return True
        return "microsoft" in f"{face.license} {face.copyright}".casefold()

    @classmethod
    def copyable(cls, face: FontFace) -> bool:
        return (not cls.comes_with_windows(face) and not face.no_embedding
                and face.path.suffix.casefold() in COPYABLE)
