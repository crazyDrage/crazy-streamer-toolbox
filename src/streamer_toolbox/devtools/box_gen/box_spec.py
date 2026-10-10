import re
from dataclasses import dataclass
from typing import Any

from streamer_toolbox.devtools.box_gen.field_spec import FieldSpec
from streamer_toolbox.devtools.box_gen.names import camel, snake

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
PATH_FIELD = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class BoxSpec:
    """One box of a service spec: its name / label / help, the request (method + path with {fields}), its
    inputs and an example answer (the answer's fields become the box's outputs)."""

    name: str
    label: str
    help: str
    method: str
    path: str
    inputs: tuple[FieldSpec, ...]
    answer_example: Any
    answer_class: str
    group: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "BoxSpec":
        name = snake(data["name"])
        request = data.get("request", {})
        method = str(request.get("method", "GET")).upper()
        if method not in METHODS:
            raise ValueError(f"box {name!r}: method is one of {', '.join(METHODS)}, not {method!r}")
        path = str(request.get("path", "")).lstrip("/")
        if path.count("{") != len(PATH_FIELD.findall(path)):
            raise ValueError(f"box {name!r}: a path field is {{name}} with letters, digits and _ only: {path!r}")
        inputs = tuple(FieldSpec.input(k, v) for k, v in (data.get("inputs") or {}).items())
        missing = set(PATH_FIELD.findall(path)) - {i.name for i in inputs}
        if missing:
            raise ValueError(f"box {name!r}: the path needs inputs {', '.join(sorted(missing))}")
        return cls(name, data.get("label") or name.replace("_", " ").capitalize(), data.get("help", ""), method,
                   path, inputs, data.get("answer_example"), data.get("answer_class") or camel(name) + "Answer",
                   data.get("group", ""))

    @property
    def path_inputs(self) -> list[FieldSpec]:
        names = PATH_FIELD.findall(self.path)
        return [i for i in self.inputs if i.name in names]

    @property
    def other_inputs(self) -> list[FieldSpec]:
        """Inputs not in the path: the query of a GET / DELETE, else the JSON body."""
        names = PATH_FIELD.findall(self.path)
        return [i for i in self.inputs if i.name not in names]

    @property
    def sends_query(self) -> bool:
        return self.method in ("GET", "DELETE")

    @property
    def has_answer_class(self) -> bool:
        return isinstance(self.answer_example, dict) and bool(self.answer_example)
