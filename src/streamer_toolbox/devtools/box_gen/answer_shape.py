from dataclasses import dataclass
from typing import Any

from streamer_toolbox.devtools.box_gen.field_spec import FieldSpec
from streamer_toolbox.devtools.box_gen.names import snake, unique


@dataclass(frozen=True)
class AnswerShape:
    """The fields of an example answer (an object): API key → Python name and kind (the toolbox's kinds, by the
    JSON type: an ID like "123" stays text). Nested objects / lists stay one field of kind object / list."""

    class_name: str
    fields: tuple[FieldSpec, ...]

    @classmethod
    def of(cls, class_name: str, example: dict[str, Any]) -> "AnswerShape":
        keys = list(example)
        names = unique([snake(k) for k in keys])
        return cls(class_name, tuple(FieldSpec(name, json_kind(example[key]), key) for name, key in zip(names, keys)))

    def outputs(self) -> dict[str, str]:
        """For actions.add(outputs=...): every field but "any" ones (a dot needs a kind)."""
        return {f.name: f.kind for f in self.fields if f.kind != "any"}

    def expected(self, example: dict[str, Any]) -> dict[str, Any]:
        """What the box gives back for the example: its fields by Python name."""
        return {f.name: example[f.key] for f in self.fields}


def json_kind(value: Any) -> str:
    if isinstance(value, bool):
        return "yes/no"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "any"
