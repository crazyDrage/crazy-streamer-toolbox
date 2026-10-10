import json
import re
import shutil
from pathlib import Path
from typing import Any

from streamer_toolbox.core.widgets.widget import Widget, check_name
from streamer_toolbox.core.widgets.widget_safety import WidgetSafety

PARTS = {"html": "widget.html", "css": "widget.css", "js": "widget.js"}
FIELDS, VALUES, KEPT, FRAME = "fields.json", "values.json", "store.json", "frame.json"
SAFETY = "safety.json"  # what the widget's page may do (WidgetSafety)
HELPERS = "helpers.json"  # the helper scripts kept on this PC: address as written → file in the media folder
STREAMELEMENTS_MEDIA = "streamelements_media.json"  # StreamElements files kept here: "<host>/<path>" → file
BLOCKED = "blocked.json"  # in the data folder: hosts the page tried that weren't allowed, with how often
BLOCKED_KEPT = 50
MEDIA = "media"  # the folder inside a widget's folder for the files that came with it (an imported Element's)
MEDIA_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
DATA = "data"  # the folder inside a widget's folder for everything it gathers while it runs
EXAMPLE = Path(__file__).parent / "example"  # a small widget in StreamElements' format that comes with the toolbox
EXAMPLE_NAME = "example_follow_box"


class WidgetStore:
    """The widgets in config/widgets/<name>/: widget.html, widget.css, widget.js and fields.json (as pasted from
    StreamElements), values.json (what he set for the fields) and, for one imported from a StreamElements
    overlay, frame.json (the box it sat in). Plain files, so a widget can also be copied in or edited by hand.

    Everything a widget gathers while it runs is in its own `data/` folder, apart from the rest of the toolbox:
    store.json (what its code keeps with SE_API.store) and the answers kept for it (channels.json,
    emotes.json; widget_router). clear_data() removes that folder in one go; the widget itself stays.

    An Element imported from StreamElements also has a `media/` folder: its pictures, videos, sounds and fonts,
    fetched once, so its page loads them from this PC (media_file gives one of them, and nothing else)."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def names(self) -> list[str]:
        if not self._folder.is_dir():
            return []
        return sorted((p.name for p in self._folder.iterdir() if p.is_dir()), key=str.casefold)

    def get(self, name: str) -> Widget | None:
        folder = self._path(name)
        if folder is None or not folder.is_dir():
            return None
        parts = {part: _text(folder / file) for part, file in PARTS.items()}
        return Widget(folder.name, fields=_object(folder / FIELDS), values=_object(folder / VALUES),
                      frame=_object(folder / FRAME), **parts)

    def save(self, widget: Widget) -> None:
        folder = self._folder / check_name(widget.name)
        folder.mkdir(parents=True, exist_ok=True)
        for part, file in PARTS.items():
            (folder / file).write_text(getattr(widget, part), encoding="utf-8")
        _write(folder / FIELDS, widget.fields)
        _write(folder / VALUES, widget.values)
        if widget.frame or (folder / FRAME).is_file():
            _write(folder / FRAME, widget.frame)

    def add_example(self) -> str:
        """Makes the example widget (latest follower + chat lines; shows every part: fields, events, a button,
        SE_API.store) unless one of that name is there; gives its name."""
        if self.get(EXAMPLE_NAME) is None:
            self.save(Widget(EXAMPLE_NAME, fields=_object(EXAMPLE / FIELDS),
                             **{part: _text(EXAMPLE / file) for part, file in PARTS.items()}))
        return EXAMPLE_NAME

    def set_values(self, name: str, values: dict[str, Any]) -> None:
        folder = self._path(name)
        if folder is None or not folder.is_dir():
            raise KeyError(f"there's no widget {name!r}")
        _write(folder / VALUES, values)

    def delete(self, name: str) -> None:
        """Removes the widget's folder with everything in it (its code, its settings, what it kept)."""
        folder = self._path(name)
        if folder is not None and folder.is_dir():
            shutil.rmtree(folder)

    def kept(self, name: str, key: str) -> Any:
        """What the widget's code stored under that key with SE_API.store.set, None if nothing."""
        folder = self._path(name)
        return self._all_kept(folder).get(key) if folder is not None else None

    def keep(self, name: str, key: str, value: Any) -> None:
        folder = self._path(name)
        if folder is None or not folder.is_dir():
            raise KeyError(f"there's no widget {name!r}")
        (folder / DATA).mkdir(exist_ok=True)
        _write(folder / DATA / KEPT, {**self._all_kept(folder), key: value})
        (folder / KEPT).unlink(missing_ok=True)  # where it was before there was a data folder

    def save_media(self, name: str, file: str, content: bytes) -> None:
        """Puts a file into the widget's media folder."""
        folder = self._path(name)
        if folder is None or not folder.is_dir():
            raise KeyError(f"there's no widget {name!r}")
        if not MEDIA_NAME.fullmatch(file):
            raise ValueError(f"not a file name: {file!r}")
        (folder / MEDIA).mkdir(exist_ok=True)
        (folder / MEDIA / file).write_bytes(content)

    def media_file(self, name: str, file: str) -> Path | None:
        """A file of the widget's media folder; None if it isn't there or the name could lead out of it."""
        folder = self._path(name)
        if folder is None or not MEDIA_NAME.fullmatch(file):
            return None
        path = folder / MEDIA / file
        return path if path.is_file() else None

    def safety(self, name: str) -> WidgetSafety:
        """What the widget's page may do; the safe start if he never changed it."""
        folder = self._path(name)
        return WidgetSafety.from_dict(_object(folder / SAFETY) if folder is not None else {})

    def set_safety(self, name: str, safety: WidgetSafety) -> None:
        folder = self._path(name)
        if folder is None or not folder.is_dir():
            raise KeyError(f"there's no widget {name!r}")
        _write(folder / SAFETY, safety.to_dict())

    def helpers(self, name: str) -> dict[str, str]:
        """The widget's helper scripts and style sheets that are kept on this PC (WidgetHelpers): the address
        as its HTML names it → the file in its media folder. Only the ones whose file is still there."""
        folder = self._path(name)
        if folder is None:
            return {}
        return {str(address): str(file) for address, file in _object(folder / HELPERS).items()
                if self.media_file(name, str(file)) is not None}

    def set_helpers(self, name: str, kept: dict[str, str]) -> None:
        folder = self._path(name)
        if folder is None or not folder.is_dir():
            raise KeyError(f"there's no widget {name!r}")
        _write(folder / HELPERS, kept)

    def streamelements_media(self, name: str) -> dict[str, str]:
        """The StreamElements files of the widget that are kept on this PC (StreamElementsMedia): "<host
        part>/<path>" as the widget's stand-in is asked → the file in its media folder. Only the ones whose
        file is still there."""
        folder = self._path(name)
        if folder is None:
            return {}
        return {str(key): str(file) for key, file in _object(folder / STREAMELEMENTS_MEDIA).items()
                if self.media_file(name, str(file)) is not None}

    def set_streamelements_media(self, name: str, kept: dict[str, str]) -> None:
        folder = self._path(name)
        if folder is None or not folder.is_dir():
            raise KeyError(f"there's no widget {name!r}")
        _write(folder / STREAMELEMENTS_MEDIA, kept)

    def blocked(self, name: str) -> dict[str, int]:
        """The hosts the widget's page tried and wasn't allowed: host → how often."""
        folder = self.data_folder(name)
        return {str(host): int(count) for host, count in _object(folder / BLOCKED).items()
                if isinstance(count, int)} if folder is not None else {}

    def note_blocked(self, name: str, host: str) -> None:
        folder = self.data_folder(name)
        if folder is None or not host:
            return
        seen = self.blocked(name)
        if host not in seen and len(seen) >= BLOCKED_KEPT:
            return
        folder.mkdir(exist_ok=True)
        _write(folder / BLOCKED, {**seen, host: seen.get(host, 0) + 1})

    def data_folder(self, name: str) -> Path | None:
        """The widget's data folder (it may not be there yet); None if there's no such widget."""
        folder = self._path(name)
        return folder / DATA if folder is not None and folder.is_dir() else None

    def data_files(self, name: str) -> dict[str, int]:
        """What is in the widget's data folder: file (with its folders) → bytes."""
        folder = self.data_folder(name)
        if folder is None or not folder.is_dir():
            return {}
        return {file.relative_to(folder).as_posix(): file.stat().st_size
                for file in sorted(folder.rglob("*")) if file.is_file()}

    def clear_data(self, name: str) -> int:
        """Removes the widget's data folder with everything in it; gives how many files went."""
        files = len(self.data_files(name))
        folder = self.data_folder(name)
        if folder is not None and folder.is_dir():
            shutil.rmtree(folder)
        return files

    @staticmethod
    def _all_kept(folder: Path) -> dict[str, Any]:
        in_data = folder / DATA / KEPT
        return _object(in_data if in_data.is_file() else folder / KEPT)

    def _path(self, name: str) -> Path | None:
        """The widget's folder; None for a name that could lead out of the widgets folder."""
        try:
            return self._folder / check_name(name)
        except ValueError:
            return None


def parse_fields(text: str) -> dict[str, dict[str, Any]]:
    """The FIELDS part as pasted: JSON text, an object of objects. Empty = no fields."""
    if not str(text).strip():
        return {}
    try:
        fields = json.loads(text)
    except ValueError as e:
        raise ValueError(f"FIELDS isn't JSON: {e}") from None
    if not isinstance(fields, dict) or not all(isinstance(spec, dict) for spec in fields.values()):
        raise ValueError('FIELDS must look like {"name": {"type": "text", "label": "...", "value": "..."}}')
    return fields


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
