from dataclasses import dataclass
from typing import Any

KINDS = ("text", "number", "yes/no", "list", "object", "any")


@dataclass(frozen=True)
class FieldSpec:
    """One field: of a box's inputs (name = the API's name, sent as is) or of an answer (key = the API's key,
    name = its Python name). kind is one of the toolbox's kinds (text, number, yes/no, list, object, any)."""

    name: str
    kind: str
    key: str = ""
    default: Any = None
    hint: str = ""

    @classmethod
    def input(cls, name: str, spec: Any) -> "FieldSpec":
        """From a spec's inputs: "number", or {"kind": "number", "default": 1, "hint": "..."}."""
        data = spec if isinstance(spec, dict) else {"kind": spec}
        kind = data.get("kind", "text")
        if kind not in KINDS:
            raise ValueError(f"input {name!r}: kind is one of {', '.join(KINDS)}, not {kind!r}")
        return cls(name, kind, name, data.get("default"), data.get("hint", ""))
