from streamer_toolbox.devtools.box_gen.answer_shape import AnswerShape
from streamer_toolbox.devtools.box_gen.box_spec import PATH_FIELD, BoxSpec
from streamer_toolbox.devtools.box_gen.field_spec import FieldSpec
from streamer_toolbox.devtools.box_gen.names import PY_TYPES, block, code_dict, literal, snake, wrapped
from streamer_toolbox.devtools.box_gen.service_spec import ServiceSpec


class ActionsClassWriter:
    """The source of a service's actions class: add_to(actions) with one box per spec box, one async handler
    each that sends the request through `send(method, path, **httpx kwargs)` (like MixItUpActions) and gives the
    answer back as its dataclass's fields."""

    def write(self, spec: ServiceSpec, answer_imports: dict[str, str]) -> str:
        """answer_imports: answer class → the module it is in."""
        uses_quote = any(b.path_inputs for b in spec.boxes)
        uses_asdict = any(b.has_answer_class for b in spec.boxes)
        lines = ["from collections.abc import Awaitable, Callable"]
        if uses_asdict:
            lines.append("from dataclasses import asdict")
        lines.append("from typing import Any")
        if uses_quote:
            lines.append("from urllib.parse import quote")
        lines += ["", "from streamer_toolbox.core.actions.action_registry import ActionRegistry"]
        lines += [f"from {module} import {name}" for name, module in sorted(answer_imports.items())]
        lines += ["", 'Send = Callable[..., Awaitable[Any]]  # (method, path, **httpx kwargs) → the answer', "", "",
                  f"class {spec.class_name}:",
                  f'    """{spec.description or spec.service + " boxes"} (made by box_gen; TODO: pickers, hints)."""',
                  "", "    def __init__(self, send: Send) -> None:", "        self._send = send", "",
                  "    def add_to(self, actions: ActionRegistry) -> None:"]
        for box in spec.boxes:
            lines += self._add(spec, box)
        for box in spec.boxes:
            lines += [""] + self._handler(box)
        if uses_quote:
            lines += ["", "", "def _part(value: Any) -> str:",
                      '    """A value as one piece of the path ("a/b" stays one piece)."""',
                      '    return quote(str(value), safe="")']
        return "\n".join(lines) + "\n"

    def _add(self, spec: ServiceSpec, box: BoxSpec) -> list[str]:
        indent = " " * 20
        lines = [f'        actions.add("{spec.service}.{box.name}", self.{box.name},',
                 indent + wrapped(box.help or box.label, 20) + ",", f"{indent}{literal(box.label)},"]
        group = box.group or spec.group
        if group:
            lines.append(f"{indent}group={literal(group)},")
        hints = {i.name: i.hint for i in box.inputs if i.hint}
        if hints:
            lines.append(f"{indent}hints={block(hints, 20, 26)},")
        if box.has_answer_class:
            outputs = AnswerShape.of(box.answer_class, box.answer_example).outputs()
            if outputs:
                lines.append(f"{indent}outputs={block(outputs, 20, 28)},")
        lines[-1] = lines[-1].rstrip(",") + ")"
        return lines

    def _handler(self, box: BoxSpec) -> list[str]:
        params = [_parameter(i) for i in sorted(box.inputs, key=lambda i: i.default is not None)]
        returns = "dict[str, Any]" if box.has_answer_class else "Any"
        lines = [f"    async def {box.name}(self{''.join(', ' + p for p in params)}) -> {returns}:"]
        if len(lines[0]) > 118:  # one parameter per line
            lines = [f"    async def {box.name}(", "            self,", *(f"            {p}," for p in params),
                     f"    ) -> {returns}:"]
        path = PATH_FIELD.sub(lambda m: "{_part(" + snake(m.group(1)) + ")}", box.path)
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
