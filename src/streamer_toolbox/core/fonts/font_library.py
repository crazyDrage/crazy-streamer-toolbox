import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

from streamer_toolbox.core.files.write_whole import write_whole
from streamer_toolbox.core.fonts.font_face import FontFace
from streamer_toolbox.core.fonts.font_reader import FontReader
from streamer_toolbox.core.fonts.installed_fonts import InstalledFonts
from streamer_toolbox.core.fonts.kept_font import KeptFont

ROUTE = "/toolbox/fonts"
CSS = f"{ROUTE}/fonts.css"  # every page loads it (his 11-18: "every font loads it from the endpoint")
FORMATS = {".ttf": "truetype", ".otf": "opentype", ".woff": "woff", ".woff2": "woff2"}
MOST_BYTES = 30 * 1024 * 1024  # a font file bigger than this isn't taken (a full CJK font is ~20 MB)
UNSAFE = re.compile(r"[^\w .()+-]")
# until the list is first changed: the fonts the font fields offered before (all come with Windows)
START_NAMES = ("Arial", "Arial Black", "Verdana", "Tahoma", "Trebuchet MS", "Segoe UI", "Georgia", "Times New Roman",
               "Courier New", "Impact", "Comic Sans MS", "Consolas") if sys.platform == "win32" else ()


class FontLibrary:
    """The fonts the toolbox knows (his 11-18): the files in its `fonts` folder (uploaded in Settings → Fonts,
    copied from this PC, or put there by hand) are hosted: every device gets them from the endpoint
    (/toolbox/fonts/fonts.css, the files under /toolbox/fonts/file/). Fonts of this PC added by name (Windows'
    own may not be hosted, temp/research/21) are in `fonts.json` next to the folder: on this machine only.

    A .woff2 needs brotli to be read; without it its family is the file name."""

    def __init__(self, folder: Path, by_name: Path, reader: FontReader | None = None) -> None:
        self.folder = folder
        self._by_name = by_name
        self._reader = reader or FontReader()
        self._seen: tuple = ()
        self._faces: list[FontFace] = []

    def fonts(self) -> list[KeptFont]:
        """Every font, sorted by name; a family that is hosted and also added by name counts as hosted."""
        hosted: dict[str, list[str]] = {}
        for face in self.faces():
            files = hosted.setdefault(face.family, [])
            if face.path.name not in files:
                files.append(face.path.name)
        fonts = [KeptFont(family, True, tuple(files)) for family, files in hosted.items()]
        known = {family.casefold() for family in hosted}
        fonts += [KeptFont(name, False) for name in self._names() if name.casefold() not in known]
        return sorted(fonts, key=lambda font: font.family.casefold())

    def not_added(self, families: dict[str, list[FontFace]]) -> dict[str, list[FontFace]]:
        """The fonts of this PC that aren't in the list yet (hosted or by name), for Add font → From this PC
        (his 11-18: the add list leaves out the fonts already added)."""
        known = {font.family.casefold() for font in self.fonts()}
        return {family: faces for family, faces in families.items() if family.casefold() not in known}

    def faces(self) -> list[FontFace]:
        """The hosted faces; read again only when the folder's files changed."""
        files = sorted(p for p in self.folder.glob("*") if p.suffix.casefold() in FORMATS and p.is_file()) \
            if self.folder.is_dir() else []
        seen = tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in files)
        if seen != self._seen:
            self._seen = seen
            self._faces = [face for path in files for face in (self._reader.read(path) or [FontFace(path.stem, path)])]
        return list(self._faces)

    def add_file(self, name: str, data: bytes) -> str:
        """An uploaded font file, kept (all devices). Its family, or ValueError."""
        suffix = Path(name).suffix.casefold()
        if suffix not in FORMATS:
            raise ValueError(f"not a font file the toolbox can host: use {', '.join(FORMATS)}")
        if len(data) > MOST_BYTES:
            raise ValueError(f"too big ({len(data) // 1024 // 1024} MB; at most {MOST_BYTES // 1024 // 1024} MB)")
        self.folder.mkdir(parents=True, exist_ok=True)
        stem = UNSAFE.sub("_", Path(name).stem).strip(" .") or "font"
        path = self.folder / f"{stem}{suffix}"
        number = 2
        while path.exists():
            path = self.folder / f"{stem} ({number}){suffix}"
            number += 1
        path.write_bytes(data)
        faces = self._reader.read(path)
        if not faces and suffix in (".ttf", ".otf"):
            path.unlink()
            raise ValueError(f"{name} isn't a font file the toolbox can read")
        return faces[0].family if faces else path.stem

    def copy_installed(self, faces: list[FontFace]) -> str:
        """Copies a font of this PC into the folder (all devices), only one that may be (InstalledFonts.copyable)."""
        allowed = [face for face in faces if InstalledFonts.copyable(face)]
        if not allowed:
            raise ValueError("this font may only be used on this machine")
        family = ""
        for path in dict.fromkeys(face.path for face in allowed):
            family = family or self.add_file(path.name, path.read_bytes())
        return family

    def add_by_name(self, family: str) -> None:
        """A font of this PC, by name only (on this machine only)."""
        family = family.strip()
        names = self._names()
        if family and family.casefold() not in {n.casefold() for n in names}:
            self._write_names([*names, family])

    def remove(self, family: str) -> list[str]:
        """Takes the font out: its files in the folder are deleted, its name leaves the list. What went."""
        gone = [face.path for face in self.faces() if face.family == family]
        for path in dict.fromkeys(gone):
            path.unlink(missing_ok=True)
        names = self._names()
        if family in names:
            self._write_names([n for n in names if n != family])
        return [p.name for p in dict.fromkeys(gone)] + ([family] if family in names else [])

    def file(self, name: str) -> Path | None:
        """A hosted file by its name, for the endpoint: only a file directly in the folder."""
        if Path(name).name != name or Path(name).suffix.casefold() not in FORMATS:
            return None
        path = self.folder / name
        return path if path.is_file() else None

    def css(self) -> str:
        """@font-face for every hosted face; the fonts of this machine need none (the browser finds them)."""
        rules = []
        for face in self.faces():
            family = face.family.replace("\\", "").replace('"', "")
            kind = FORMATS[face.path.suffix.casefold()]
            rules.append(f'@font-face {{ font-family: "{family}"; src: url("{ROUTE}/file/{quote(face.path.name)}") '
                         f'format("{kind}"); font-weight: {face.weight}'
                         f'{f" {face.weight_most}" if face.weight_most else ""}; '
                         f'font-style: {"italic" if face.italic else "normal"}; font-display: swap; }}')
        return "\n".join(rules) + "\n"

    def _names(self) -> list[str]:
        if not self._by_name.exists():
            return list(START_NAMES)
        try:
            data = json.loads(self._by_name.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [str(n) for n in data.get("this_machine", [])] if isinstance(data, dict) else []

    def _write_names(self, names: list[str]) -> None:
        self._by_name.parent.mkdir(parents=True, exist_ok=True)
        write_whole(self._by_name, json.dumps({"this_machine": names}, indent=2, ensure_ascii=False))
