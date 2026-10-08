from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JsonBoxField:
    """One field of a box that is written in a JSON file (see JsonBoxes for the file).

    `name` is the field in the box, `send_as` the name the program wants ("sceneName"; the same as `name` when
    left out), `kind` a value kind's name (ValueKinds) or "choice" with `choices`. An `optional` field that is
    left empty is not sent; one that is not optional must be filled in. `default` is what the field holds in
    a new box (else the kind's)."""

    name: str
    kind: str = "text"
    label: str = ""
    hint: str = ""
    optional: bool = False
    default: Any = None
    send_as: str = ""
    choices: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonBoxField":
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown or "name" not in data:
            raise ValueError(f"a field needs \"name\" and may have kind, label, hint, optional, default, send_as, "
                             f"choices (got {', '.join(sorted(data))})")
        return cls(**{**data, "choices": tuple(data.get("choices", ()))})

    @property
    def sent_name(self) -> str:
        return self.send_as or self.name
