import json
import re
from collections.abc import Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.flow_editor.move_buttons import move_buttons

LINE_NAME = re.compile(r"\w+")  # a line is wired as ${box.n3.<name>}


class ValueLinesInput:
    """The lines of a Value box: a name and a value each, "Add value" for one more, ↑ / ↓ to move one and x to take
    one away, "From variable" for a line holding a variable's value as it is now (his round 60: a copy, typed
    in, not the live variable). Every line is an orange dot of its own on the box, in the same order.

    on_change(lines, moved) gets the new {name: value} each time; moved is None while a value is typed, else the
    dots changed: (old, new) for a renamed line, whose wires follow it, (old, "") for one taken away, ("", "")
    for one added or moved (or a name that wasn't taken: the form shows the old one again)."""

    def __init__(self, lines: dict[str, Any], on_change: Callable[[dict[str, Any], tuple[str, str] | None], None],
                 hint: str = "", variables: VariableStore | None = None) -> None:
        self._lines = dict(lines)
        self._variables = variables
        self._on_change = on_change
        self._hint = hint

    def build(self) -> None:
        with ui.column().classes("w-full gap-1"):
            ui.label("values").classes("text-sm font-semibold")
            for number, (name, value) in enumerate(self._lines.items(), 1):
                with ui.row().classes("items-center no-wrap w-full gap-2"):
                    ui.input("name", value=name).props("outlined dense").classes("w-32 shrink-0") \
                        .on("blur", lambda e, n=name: self._rename(n, e.sender.value))
                    ui.input("value", value="" if value is None else str(value),
                             on_change=lambda e, n=name: self._set(n, e.value)) \
                        .props("outlined dense").classes("flex-1 min-w-0")
                    if len(self._lines) > 1:
                        move_buttons(number, len(self._lines), lambda step, n=name: self._move(n, step))
                    ui.button(icon="close", on_click=lambda n=name: self._remove(n)) \
                        .props("flat round dense size=sm").tooltip("Take this value away (and its dot)")
            with ui.row().classes("gap-1"):
                ui.button("Add value", icon="add", on_click=self._add).props("no-caps outline dense")
                if self._variables is not None:
                    ui.button("From variable", icon="data_object", on_click=self._from_variable) \
                        .props("no-caps outline dense").tooltip("A line with a variable's value as it is now")
            if self._hint:
                ui.label(self._hint).classes("text-xs opacity-60")

    def _set(self, name: str, value: str) -> None:
        self._lines[name] = value
        self._on_change(dict(self._lines), None)

    def _rename(self, old: str, new: str) -> None:
        new = (new or "").strip().replace(" ", "_")
        if new == old:
            return
        if not LINE_NAME.fullmatch(new):
            ui.notify("A name takes letters, digits and _ only", type="warning")
        elif new in self._lines:
            ui.notify(f"There is a value named {new} already", type="warning")
        else:
            self._lines = {new if k == old else k: v for k, v in self._lines.items()}
            self._on_change(dict(self._lines), (old, new))
            return
        self._on_change(dict(self._lines), ("", ""))  # the form shows the old name again

    def _add(self) -> None:
        number = len(self._lines) + 1
        while f"value_{number}" in self._lines:
            number += 1
        self._lines[f"value_{number}"] = ""
        self._on_change(dict(self._lines), ("", ""))

    async def _from_variable(self) -> None:
        names = sorted(self._variables.names(), key=str.casefold)
        if not names:
            ui.notify("No variables yet", type="info")
            return
        with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full gap-3"):
            ui.label("A value from a variable").classes("font-semibold")
            ui.label("The line gets the variable's value as it is now: changing the variable later doesn't change "
                     "the line.").classes("text-xs opacity-70")
            picked = ui.select(names, label="Variable", with_input=True).props("outlined dense").classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Add", on_click=lambda: dialog.submit(picked.value)).props("unelevated no-caps")
        name = await dialog
        dialog.delete()
        if name:
            self.add_variable(name)

    def add_variable(self, name: str) -> None:
        """A line named like the variable (model_pos_2 if taken) holding its value as typed text: JSON for an
        object or a list, so it reads back as the same kind."""
        value = self._variables.get(name)
        line, number = name, 2
        while line in self._lines:
            line, number = f"{name}_{number}", number + 1
        self._lines[line] = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        self._on_change(dict(self._lines), ("", ""))

    def _move(self, name: str, step: int) -> None:
        names = list(self._lines)
        index = names.index(name)
        if 0 <= index + step < len(names):
            names[index], names[index + step] = names[index + step], names[index]
            self._lines = {n: self._lines[n] for n in names}
            self._on_change(dict(self._lines), ("", ""))

    def _remove(self, name: str) -> None:
        self._lines.pop(name, None)
        self._on_change(dict(self._lines), (name, ""))
