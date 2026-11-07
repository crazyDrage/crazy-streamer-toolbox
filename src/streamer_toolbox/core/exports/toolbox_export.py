import io
import json
import zipfile
from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.app_version import APP_VERSION
from streamer_toolbox.core.upgrades.settings_version import SETTINGS_VERSION, VERSION_KEY

FORMAT_KEY = "toolbox_export"  # in manifest.json: this is an export, and the format's number
FORMAT = 1
MANIFEST = "manifest.json"
ENDING = ".toolbox"
MOST_BYTES = 2 * 1024 ** 3  # an export that unpacks to more is refused (a broken or harmful file)


@dataclass
class ToolboxExport:
    """A `.toolbox` file (his round 86: one file with everything connected): a zip with manifest.json and the
    files that came along. The manifest has the format's number, the settings version and the toolbox version
    it was made with, its title, and one entry per part: {kind, key, title, data, files}. `data` is what the
    toolbox keeps for that part (an alert's to_dict, a flow's file, ...); `files` maps a file the data names
    (a picture's path as it was on the PC that made it, a widget's own file) to its place in the zip.

    Never inside: tokens, keys, accounts (they are in secrets/, which no part reads)."""

    title: str
    entries: list[dict[str, Any]] = field(default_factory=list)
    files: dict[str, bytes] = field(default_factory=dict)
    settings_version: int = SETTINGS_VERSION
    app_version: str = APP_VERSION

    def to_bytes(self) -> bytes:
        manifest = {FORMAT_KEY: FORMAT, VERSION_KEY: self.settings_version, "app_version": self.app_version,
                    "title": self.title, "parts": self.entries}
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST, json.dumps(manifest, indent=1, ensure_ascii=False))
            for name, content in self.files.items():
                archive.writestr(name, content)
        return out.getvalue()

    @classmethod
    def from_bytes(cls, content: bytes) -> "ToolboxExport":
        """ValueError with a reason he can read: not an export, made by a newer toolbox, broken."""
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile:
            raise ValueError("this is not a toolbox export (not a zip file)") from None
        with archive:
            names = archive.namelist()
            if MANIFEST not in names:
                raise ValueError("this is not a toolbox export (it has no manifest.json)")
            if sum(info.file_size for info in archive.infolist()) > MOST_BYTES:
                raise ValueError("this export unpacks to more than 2 GB: refused")
            try:
                manifest = json.loads(archive.read(MANIFEST).decode("utf-8"))
            except ValueError as e:
                raise ValueError(f"this export's manifest.json is broken: {e}") from None
            if not isinstance(manifest, dict) or FORMAT_KEY not in manifest:
                raise ValueError("this is not a toolbox export")
            if manifest[FORMAT_KEY] != FORMAT:
                raise ValueError(f"this export was made by a newer toolbox (format {manifest[FORMAT_KEY]!r}): "
                                 "update this toolbox first")
            entries = [e for e in manifest.get("parts", []) if isinstance(e, dict) and e.get("kind") and e.get("key")]
            wanted = {place for e in entries for place in (e.get("files") or {}).values()}
            files = {name: archive.read(name) for name in names if name in wanted and _safe(name)}
        return cls(str(manifest.get("title") or "Import"), entries, files, int(manifest.get(VERSION_KEY, 0)),
                   str(manifest.get("app_version") or "?"))

    def size(self) -> int:
        return sum(len(content) for content in self.files.values())


def _safe(name: str) -> bool:
    """A place inside the zip that can't lead out of a folder it is unpacked into."""
    parts = name.replace("\\", "/").split("/")
    return bool(name) and not name.startswith(("/", "\\")) and ".." not in parts and ":" not in parts[0]
