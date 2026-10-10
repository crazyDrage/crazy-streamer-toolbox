import re
from dataclasses import dataclass, field
from typing import Any

NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
MEDIA_FIELDS = ("image-input", "video-input", "sound-input")  # their value is a file on this PC
NO_VALUE = ("button",)  # a field that only does something when pressed


@dataclass(frozen=True)
class Widget:
    """A custom widget in StreamElements' format: the four parts people share (HTML, CSS, JS and FIELDS, the
    settings its code asks for as {name: {type, label, value, ...}}), the values he set for those fields, and
    `frame`: the box it sat in on a StreamElements overlay (width, height, top, left; empty = the whole page)."""

    name: str
    html: str = ""
    css: str = ""
    js: str = ""
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)
    frame: dict[str, Any] = field(default_factory=dict)

    def field_data(self) -> dict[str, Any]:
        """What the widget's code gets as fieldData: every field's start value, with his own on top."""
        data = {key: spec.get("value", "") for key, spec in self.fields.items() if spec.get("type") not in NO_VALUE}
        data.update({key: value for key, value in self.values.items() if key in data})
        return data

    def media_fields(self) -> list[str]:
        return [key for key, spec in self.fields.items() if spec.get("type") in MEDIA_FIELDS]


def check_name(name: str) -> str:
    """A widget's name is its folder and part of its address: letters, digits, _ and -."""
    name = str(name).strip()
    if not NAME.fullmatch(name):
        raise ValueError("a widget's name is letters, digits, _ and - (no spaces), e.g. chat_box")
    return name
