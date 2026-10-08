from streamer_toolbox.devtools.box_gen.answer_shape import AnswerShape
from streamer_toolbox.devtools.box_gen.names import EMPTY, PY_TYPES, literal


class AnswerClassWriter:
    """The source of a frozen dataclass for one answer shape, with from_answer(dict) reading the API's keys."""

    def write(self, shape: AnswerShape, service: str, box: str) -> str:
        uses_field = any(f.kind in ("list", "object") for f in shape.fields)
        lines = [f"from dataclasses import dataclass{', field' if uses_field else ''}",
                 "from typing import Any", "", "", "@dataclass(frozen=True)", f"class {shape.class_name}:",
                 f'    """What {service}.{box} answers (made from an example answer by box_gen)."""', ""]
        for f in shape.fields:
            if f.kind in ("list", "object"):
                factory = "list" if f.kind == "list" else "dict"
                lines.append(f"    {f.name}: {PY_TYPES[f.kind]} = field(default_factory={factory})")
            else:
                lines.append(f"    {f.name}: {PY_TYPES[f.kind]}{' | None' if f.kind == 'any' else ''} = "
                             f"{EMPTY[f.kind]}")
        lines += ["", "    @classmethod",
                  f'    def from_answer(cls, answer: dict[str, Any]) -> "{shape.class_name}":',
                  "        return cls("]
        for f in shape.fields:
            default = {"list": "[]", "object": "{}"}.get(f.kind, EMPTY.get(f.kind, "None"))
            lines.append(f"            {f.name}=answer.get({literal(f.key)}, {default}),")
        lines.append("        )")
        return "\n".join(lines) + "\n"
