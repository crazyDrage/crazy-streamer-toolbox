from streamer_toolbox.devtools.box_gen.answer_shape import AnswerShape
from streamer_toolbox.devtools.box_gen.box_spec import PATH_FIELD, BoxSpec
from streamer_toolbox.devtools.box_gen.field_spec import FieldSpec
from streamer_toolbox.devtools.box_gen.names import PY_TYPES, block, camel, code_dict, literal, snake, wrapped
from streamer_toolbox.devtools.box_gen.service_spec import ServiceSpec


class BoxClassWriter:
    """The sources of a service's boxes, one Box class per file (like every box of the toolbox): `base` is the
    class they share (it keeps `send(method, path, **httpx kwargs)`, like MixItUpBox), `box` one box that sends
    its request and gives the answer back as its dataclass's fields."""

    @staticmethod
    def base_class(spec: ServiceSpec) -> str:
        return camel(spec.service) + "Box"

    @staticmethod
    def class_of(box: BoxSpec) -> str:
        return camel(box.name)

    def base(self, spec: ServiceSpec) -> str:
        uses_quote = any(b.path_inputs for b in spec.boxes)
        lines = ["from collections.abc import Awaitable, Callable", "from typing import Any"]
        if uses_quote:
            lines.append("from urllib.parse import quote")
        lines += ["", "from streamer_toolbox.core.interfaces.box import Box", "",
                  "Send = Callable[..., Awaitable[Any]]  # (method, path, **httpx kwargs) → the answer", "", "",
                  f"class {self.base_class(spec)}(Box):",
                  f'    """What the {spec.service} boxes share: `send` sends a request (made by box_gen; no run, so not '
                  'a box)."""', "",
                  "    def __init__(self, send: Send) -> None:", "        self._send = send"]
        if uses_quote:
            lines += ["", "", "def path_part(value: Any) -> str:",
                      '    """A value as one piece of the path ("a/b" stays one piece)."""',
                      '    return quote(str(value), safe="")']
        return "\n".join(lines) + "\n"

    def box(self, spec: ServiceSpec, box: BoxSpec, base_module: str, answer_imports: dict[str, str]) -> str:
        """answer_imports: answer class → the module it is in."""
        lines = []
        if box.has_answer_class:
            lines.append("from dataclasses import asdict")
        lines += ["from typing import Any", ""]
        if box.has_answer_class:
            lines.append(f"from {answer_imports[box.answer_class]} import {box.answer_class}")
        base_names = [self.base_class(spec)] + (["path_part"] if box.path_inputs else [])
        lines.append(f"from {base_module} import {', '.join(base_names)}")
        lines += ["", "", f"class {self.class_of(box)}({self.base_class(spec)}):",
                  f"    name = {literal(box.name)}", f"    label = {literal(box.label)}"]
        text = wrapped(box.help or box.label, 12)
        lines.append(f"    help = ({text})" if "\n" in text else f"    help = {text}")
        group = box.group or spec.group
        if group:
            lines.append(f"    group = {literal(group)}")
        hints = {i.name: i.hint for i in box.inputs if i.hint}
        if hints:
            lines.append(f"    hints = {block(hints, 4, 12)}")
        if box.has_answer_class:
            outputs = AnswerShape.of(box.answer_class, box.answer_example).outputs()
            if outputs:
                lines.append(f"    outputs = {block(outputs, 4, 14)}")
        lines += [""] + self._run(box)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _run(box: BoxSpec) -> list[str]:
        params = [_parameter(i) for i in sorted(box.inputs, key=lambda i: i.default is not None)]
        returns = "dict[str, Any]" if box.has_answer_class else "Any"
        lines = [f"    async def run(self{''.join(', ' + p for p in params)}) -> {returns}:"]
        if len(lines[0]) > 118:  # one parameter per line
            lines = ["    async def run(", "            self,", *(f"            {p}," for p in params),
                     f"    ) -> {returns}:"]
        path = PATH_FIELD.sub(lambda m: "{path_part(" + snake(m.group(1)) + ")}", box.path)
        call = f'self._send("{box.method}", f"{path}"' if box.path_inputs else f'self._send("{box.method}", "{path}"'
        start = "        answer = await " if box.has_answer_class else "        return await "
        others = box.other_inputs
        if others:
            key = "params" if box.sends_query else "json"
            call += f", {key}="
            call += code_dict([(i.name, snake(i.name)) for i in others], 8, len(start) + len(call))
        call += ")"
        lines.append(start + call)
        if box.has_answer_class:
            lines.append(f"        return asdict({box.answer_class}.from_answer(answer))")
        return lines


def _parameter(field: FieldSpec) -> str:
    text = f"{snake(field.name)}: {PY_TYPES[field.kind]}"
    return text if field.default is None else f"{text} = {literal(field.default)}"
