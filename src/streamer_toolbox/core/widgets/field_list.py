import re
from typing import Any

# a FIELDS type → what it is, for the list's type dropdown (WidgetFieldsForm draws each of them)
KINDS = {
    "text": "Text: one line",
    "textarea": "Text: several lines",
    "number": "Number",
    "slider": "Slider (a number between min and max)",
    "checkbox": "On / off",
    "colorpicker": "Colour",
    "dropdown": "Dropdown (choices)",
    "googleFont": "Font",
    "image-input": "Picture (a file)",
    "video-input": "Video (a file)",
    "sound-input": "Sound (a file)",
    "button": "Button (sends an event to the widget)",
    "hidden": "Hidden (a value the code reads, no input)",
}
NUMBERS = ("number", "slider")  # the types that have min / max / step
LIMITS = ("min", "max", "step")
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")


class FieldList:
    """A widget's FIELDS as a list to change row by row (his round 72: "a list view with dropdown for options like
    type"): every change gives the whole FIELDS again, in their order, so the list and the code are the same
    thing. A field is {type, label, value, group, ...} under its name; the name is what the code reads
    ({{name}}, fieldData.name)."""

    def __init__(self, fields: dict[str, dict[str, Any]]) -> None:
        self.fields = {key: dict(spec) for key, spec in fields.items()}

    def add(self, kind: str = "text") -> str:
        """A new field at the end (the list's Add button is on top, so it shows where it lands); its name."""
        taken, number = set(self.fields), 1
        while f"setting{number}" in taken:
            number += 1
        name = f"setting{number}"
        self.fields[name] = {"type": kind, "label": f"Setting {number}", "value": _start(kind)}
        return name

    def remove(self, name: str) -> None:
        self.fields.pop(name, None)

    def rename(self, old: str, new: str) -> None:
        """Same place in the order. A name the code can't read ({{my name}}) or one that is taken: ValueError."""
        new = new.strip()
        if new == old:
            return
        if not NAME.fullmatch(new):
            raise ValueError("a setting's name is letters, digits, _ and - (no spaces, not starting with a "
                             "digit), e.g. textColor")
        if new in self.fields:
            raise ValueError(f"there's a setting {new!r} already")
        self.fields = {new if key == old else key: spec for key, spec in self.fields.items()}

    def up(self, name: str) -> None:
        keys = list(self.fields)
        at = keys.index(name)
        if at:
            keys[at - 1], keys[at] = keys[at], keys[at - 1]
            self.fields = {key: self.fields[key] for key in keys}

    def set(self, name: str, part: str, value: Any) -> None:
        """One part of a field (type, label, value, group, min, max, step, options). "" for group / a limit
        takes it away. A new type keeps the label, gets a start value that fits it and drops what it can't have
        (min / max / step, options)."""
        spec = self.fields[name]
        if part == "type":
            if value != spec.get("type"):
                spec["value"] = _start(value) if not _fits(value, spec.get("value")) else spec.get("value")
                for limit in LIMITS:
                    if value not in NUMBERS:
                        spec.pop(limit, None)
                if value != "dropdown":
                    spec.pop("options", None)
                elif not isinstance(spec.get("options"), dict):
                    spec["options"] = {"one": "One", "two": "Two"}
                    spec["value"] = "one"
            spec["type"] = value
        elif part in ("group", *LIMITS) and value in ("", None):
            spec.pop(part, None)
        else:  # 1920.0 → 1920: a number input gives floats (his chat widget's FIELDS had "max": 1920.0)
            spec[part] = int(value) if isinstance(value, float) and value.is_integer() else value

    @staticmethod
    def options_text(options: Any) -> str:
        """A dropdown's choices as lines "value: what it shows"."""
        if not isinstance(options, dict):
            return ""
        return "\n".join(f"{key}: {label}" if label != key else str(key) for key, label in options.items())

    @staticmethod
    def options_from(text: str) -> dict[str, str]:
        """Lines "value: what it shows" (or just "value") → a dropdown's choices."""
        options: dict[str, str] = {}
        for line in text.splitlines():
            key, colon, label = line.partition(":")
            if key.strip():
                options[key.strip()] = label.strip() if colon and label.strip() else key.strip()
        return options


def _start(kind: str) -> Any:
    return {"number": 0, "slider": 50, "checkbox": False, "colorpicker": "#ffffff"}.get(kind, "")


def _fits(kind: str, value: Any) -> bool:
    if kind in NUMBERS:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "checkbox":
        return isinstance(value, bool)
    return isinstance(value, str)
