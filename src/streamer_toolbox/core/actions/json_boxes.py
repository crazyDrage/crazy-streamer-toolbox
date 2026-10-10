import inspect
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.json_box import JsonBox
from streamer_toolbox.core.actions.json_box_field import JsonBoxField
from streamer_toolbox.core.actions.registered_action import ActionHandler
from streamer_toolbox.core.values.value_kinds import CHOICE, ValueKinds

Send = Callable[[str, dict[str, Any]], Awaitable[Any]]  # (request, data) → the program's answer


class JsonBoxes:
    """Boxes that are written as JSON, not as Python: every `*.json` file in a folder holds some boxes of one
    program, each a request to send with the fields to fill in. For what needs no code of its own; a box that
    does more than send one request (asks first, waits, works something out) stays a class.

        {"group": "Windows",
         "boxes": [{"name": "open_source_projector", "label": "Open source projector",
                    "help": "Opens a projector window for a source",
                    "request": "OpenSourceProjector",
                    "fields": [{"name": "source", "send_as": "sourceName", "kind": "obs.source"},
                               {"name": "monitor", "send_as": "monitorIndex", "kind": "whole_number",
                                "optional": true, "default": -1, "hint": "-1 = a window"}]}]}

    A field's `kind` is a value kind's name (ValueKinds: the global ones, and the special ones given here), or
    "choice" with its own "choices". add_to gives every box to the registry as <category>.<name>; running it
    calls send(request, data) with the fields under the names the program wants."""

    def __init__(self, folder: Path, kinds: ValueKinds | None = None) -> None:
        self._kinds = kinds or ValueKinds()
        self.boxes: list[JsonBox] = []
        for file in sorted(folder.glob("*.json")):
            try:
                content = json.loads(file.read_text(encoding="utf-8"))
                boxes = [JsonBox.from_dict(box, content.get("group", "")) for box in content["boxes"]]
                for box in boxes:
                    self._check(box)
            except (ValueError, KeyError, TypeError, AttributeError) as e:
                raise ValueError(f"{file.name}: {e}") from None
            self.boxes += boxes

    def add_to(self, actions: ActionRegistry, category: str, send: Send) -> None:
        for box in self.boxes:
            actions.add(f"{category}.{box.name}", self._handler(box, send), box.help, box.label, group=box.group,
                        flow_only=box.flow_only, labels={f.name: f.label for f in box.fields if f.label},
                        hints={f.name: f.hint for f in box.fields if f.hint}, **self._extras(box))

    def _check(self, box: JsonBox) -> None:
        for field in box.fields:
            if field.kind == CHOICE:
                if not field.choices:
                    raise ValueError(f"box {box.name!r}, field {field.name!r}: a choice needs \"choices\"")
            else:
                try:
                    self._kinds.get(field.kind)
                except ValueError as e:
                    raise ValueError(f"box {box.name!r}, field {field.name!r}: {e}") from None

    def _extras(self, box: JsonBox) -> dict[str, Any]:
        """The box extras its fields' kinds ask for: {"colors": ("tint",), "options": {"scene": provider}}."""
        extras: dict[str, Any] = {}
        for field in box.fields:
            if field.kind == CHOICE:
                extras.setdefault("options", {})[field.name] = _fixed_choices(field.choices)
                continue
            kind = self._kinds.get(field.kind)
            if kind.extra == "colors":
                extras["colors"] = (*extras.get("colors", ()), field.name)
            elif kind.extra:
                extras.setdefault(kind.extra, {})[field.name] = kind.setting
        return extras

    def _handler(self, box: JsonBox, send: Send) -> ActionHandler:
        async def run(**values: Any) -> dict[str, Any]:
            data = dict(box.fixed)
            for field in box.fields:
                value = values.get(field.name, self._default(field))
                if value in ("", None):
                    if not field.optional:
                        raise ValueError(f"{box.label or box.name}: {field.label or field.name} is empty")
                    continue
                try:
                    data[field.sent_name] = value if field.kind == CHOICE else self._kinds.get(field.kind).sent(value)
                except ValueError as e:
                    raise ValueError(f"{box.label or box.name}, {field.label or field.name}: {e}") from None
            return await send(box.request, data)

        # the box form reads the fields from the handler's parameters, like any box's
        run.__signature__ = inspect.Signature(
            [inspect.Parameter(field.name, inspect.Parameter.KEYWORD_ONLY, default=self._default(field),
                               annotation=str if field.kind == CHOICE else self._kinds.get(field.kind).annotation)
             for field in box.fields], return_annotation=dict[str, Any])
        run.__name__ = box.name
        return run

    def _default(self, field: JsonBoxField) -> Any:
        if field.default is not None:
            return field.default
        return "" if field.kind == CHOICE else self._kinds.get(field.kind).default


def _fixed_choices(choices: tuple[str, ...]) -> Callable[[], Awaitable[list[str]]]:
    async def provider() -> list[str]:
        return list(choices)
    return provider
