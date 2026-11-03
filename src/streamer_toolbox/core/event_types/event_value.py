import re
from dataclasses import dataclass
from typing import Any

# what a value holds → its name in the Events tab (his round 78 list)
KINDS = {"text": "Text", "number": "Number", "colour": "Colour", "yes_no": "Yes/No", "picture": "Picture",
         "sound": "Sound"}
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
YES_NO = {"true": True, "yes": True, "1": True, "false": False, "no": False, "0": False}


@dataclass(frozen=True)
class EventValue:
    """One value an event type carries (his round 77: "value name, default value", and a type: picture, sound,
    ...): its name, what it is when the flow gives nothing, its kind, and the names other programs' code reads
    it as (StreamElements' follower-latest calls the user `name`), so an imported widget gets it by itself."""

    name: str
    default: str = ""
    kind: str = "text"
    also_known_as: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventValue":
        kind = data.get("kind")
        return cls(str(data.get("name") or "value"), str(data.get("default", "")), kind if kind in KINDS else "text",
                   names_in(data.get("also_known_as", ())))

    def value(self, given: Any) -> Any:
        """What it holds for one send: the default when the flow gave nothing; a number value a number and a
        Yes/No value true / false when it can be read as one (rule 25: the rest stays as it came)."""
        if given is None or given == "":
            given = self.default
        if self.kind == "number" and isinstance(given, str):
            try:
                number = float(given)
                return int(number) if number.is_integer() else number
            except ValueError:
                return given
        if self.kind == "yes_no" and isinstance(given, str) and given.strip().casefold() in YES_NO:
            return YES_NO[given.strip().casefold()]
        return given

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name, "default": self.default, "kind": self.kind}
        if self.also_known_as:
            data["also_known_as"] = list(self.also_known_as)
        return data


def check_value_name(name: str) -> str:
    name = str(name).strip()
    if not NAME.fullmatch(name):
        raise ValueError("a value's name is letters, digits and _ (no spaces), e.g. user or displayName")
    return name


def names_in(given: Any) -> tuple[str, ...]:
    """'follower-latest, name' or a list → its names, once each, in their order."""
    parts = re.split(r"[,\s]+", given) if isinstance(given, str) else [str(p) for p in given or ()]
    return tuple(dict.fromkeys(p.strip() for p in parts if p.strip()))
