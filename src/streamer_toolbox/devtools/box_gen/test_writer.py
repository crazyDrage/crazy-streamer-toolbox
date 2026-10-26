from typing import Any
from urllib.parse import quote

from streamer_toolbox.devtools.box_gen.answer_shape import AnswerShape
from streamer_toolbox.devtools.box_gen.box_spec import PATH_FIELD, BoxSpec
from streamer_toolbox.devtools.box_gen.field_spec import FieldSpec
from streamer_toolbox.devtools.box_gen.names import block, literal, snake
from streamer_toolbox.devtools.box_gen.service_spec import ServiceSpec

EXAMPLES = {"text": "example", "number": 1, "yes/no": True, "list": [], "object": {}, "any": "example"}


class TestWriter:
    """The source of a unittest file for a generated actions class: per box, the request it sends (method,
    path, query / body) and what it gives back for the spec's example answer."""

    def write(self, spec: ServiceSpec, actions_module: str, fake_module: str, fake_class: str) -> str:
        test_class = f"Test{spec.class_name}"
        lines = ["import unittest", "", "from streamer_toolbox.core.actions.action_registry import ActionRegistry",
                 f"from {actions_module} import {spec.class_name}", f"from {fake_module} import {fake_class}", ""]
        for box in spec.boxes:
            lines += _constant(f"ANSWER_{box.name.upper()}", box.answer_example)
        lines += ["", "", f"class {test_class}(unittest.IsolatedAsyncioTestCase):",
                  '    """Made by box_gen from the spec\'s examples: add real cases here."""', "",
                  "    def setUp(self) -> None:", f"        self.send = {fake_class}()",
                  "        self.actions = ActionRegistry()",
                  f"        {spec.class_name}(self.send).add_to(self.actions)"]
        for box in spec.boxes:
            lines += [""] + self._test(spec, box)
        lines += ["", "", 'if __name__ == "__main__":', "    unittest.main()"]
        return "\n".join(lines) + "\n"

    def _test(self, spec: ServiceSpec, box: BoxSpec) -> list[str]:
        values = {i.name: _example(i) for i in box.inputs}
        path = PATH_FIELD.sub(lambda m: quote(str(values[m.group(1)]), safe=""), box.path)
        others = {i.name: values[i.name] for i in box.other_inputs}
        sent = {("params" if box.sends_query else "json"): others} if others else {}
        arguments = [f"{snake(k)}={literal(v)}" for k, v in values.items()]
        answer = f"ANSWER_{box.name.upper()}"
        run = f'        result = await self.actions.run("{spec.service}.{box.name}"'
        run += "".join(", " + a for a in arguments) + ")"
        if len(run) > 118:
            run = "\n".join(["        result = await self.actions.run(", f'            "{spec.service}.{box.name}",',
                             *(f"            {a}," for a in arguments), "        )"])
        call = (box.method, path, sent)
        lines = [f"    async def test_{box.name}(self) -> None:",
                 f"        self.send.answers[({literal(box.method)}, {literal(path)})] = {answer}", run,
                 f"        self.assertEqual(self.send.calls, {block([call], 8, 36)})"]
        if box.has_answer_class:
            expected = AnswerShape.of(box.answer_class, box.answer_example).expected(box.answer_example)
            lines += _constant("expected", expected, indent_by=8)
            lines.append("        self.assertEqual(result, expected)")
        else:
            lines.append(f"        self.assertEqual(result, {answer})")
        return lines


def _example(field: FieldSpec) -> Any:
    return field.default if field.default is not None else EXAMPLES[field.kind]


def _constant(name: str, value: Any, indent_by: int = 0) -> list[str]:
    """name = value, a long dict / list one item per line, indented like the code around it."""
    pad = " " * indent_by
    return (f"{pad}{name} = " + block(value, indent_by, indent_by + len(name) + 3)).split("\n")
