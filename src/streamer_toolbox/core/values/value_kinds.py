import json
from collections.abc import Iterable
from typing import Any

from streamer_toolbox.core.files.file_types import (ANY_FILE, AUDIO_TYPES, FOLDER, IMAGE_TYPES, MEDIA_TYPES,
                                                    VIDEO_TYPES)
from streamer_toolbox.core.values.value_kind import ValueKind

CHOICE = "choice"  # a field with its own short list (the field names the choices), not a kind of its own


class ValueKinds:
    """The value kinds a box field can name. The global ones are always there:

        text, number, whole_number, yes_no, color, list, object,
        file, folder, image, sound, video, media

    A connection or plugin adds its special ones ("obs.scene": a picker that asks the program). A kind that
    needs its own window (a VTube Studio animation) is still written in Python; once it is added here under a
    name, a box from a JSON file can use it."""

    def __init__(self, special: Iterable[ValueKind] = ()) -> None:
        self._kinds: dict[str, ValueKind] = {}
        for kind in (*_global_kinds(), *special):
            self.add(kind)

    def add(self, kind: ValueKind) -> None:
        if kind.name in self._kinds or kind.name == CHOICE:
            raise ValueError(f"value kind {kind.name!r} is already there")
        self._kinds[kind.name] = kind

    def get(self, name: str) -> ValueKind:
        if name not in self._kinds:
            raise ValueError(f"unknown value kind {name!r} (known: {', '.join(self.names())})")
        return self._kinds[name]

    def names(self) -> list[str]:
        return sorted(self._kinds)

    def __contains__(self, name: str) -> bool:
        return name in self._kinds


def _global_kinds() -> list[ValueKind]:
    files = {"file": ("File", ANY_FILE), "folder": ("Folder", FOLDER), "image": ("Picture", IMAGE_TYPES),
             "sound": ("Sound", AUDIO_TYPES), "video": ("Video", VIDEO_TYPES), "media": ("Video or sound", MEDIA_TYPES)}
    return [ValueKind("text", "Text"),
            ValueKind("number", "Number", float, 0.0, parse=_number),
            ValueKind("whole_number", "Whole number", int, 0, parse=_whole_number),
            ValueKind("yes_no", "Yes / no", bool, False, parse=_yes_no),
            ValueKind("color", "Colour", extra="colors"),
            ValueKind("list", "List", parse=lambda value: _json(value, list, "a list like [1, 2]")),
            ValueKind("object", "Object", parse=lambda value: _json(value, dict, 'an object like {"name": 1}')),
            *(ValueKind(name, title, extra="files", setting=endings) for name, (title, endings) in files.items())]


def _number(value: Any) -> float | int:
    if isinstance(value, bool):
        raise ValueError(f"{value!r} is not a number")
    try:
        number = value if isinstance(value, (int, float)) else float(str(value).strip())
    except ValueError:
        raise ValueError(f"{value!r} is not a number") from None
    return int(number) if float(number).is_integer() else number


def _whole_number(value: Any) -> int:
    number = _number(value)
    if not isinstance(number, int):
        raise ValueError(f"{value!r} is not a whole number")
    return number


def _yes_no(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().casefold()
    if text in ("true", "yes", "1", "on"):
        return True
    if text in ("false", "no", "0", "off"):
        return False
    raise ValueError(f"{value!r} is not yes or no")


def _json(value: Any, wanted: type, like: str) -> Any:
    """A list or an object: as it is (from a variable or a wire), or from JSON text typed into the field."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError(f"{value!r} is not {like}") from None
    if not isinstance(value, wanted):
        raise ValueError(f"{value!r} is not {like}")
    return value
