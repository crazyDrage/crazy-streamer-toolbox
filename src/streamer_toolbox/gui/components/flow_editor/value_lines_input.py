import re
from collections.abc import Callable
from typing import Any

from nicegui import ui

LINE_NAME = re.compile(r"\w+")  # a line is wired as ${box.n3.<name>}


class ValueLinesInput:
    """The lines of a Value box: a name and a value each, "Add value" for one more and x to take one away. Every
    line is an orange dot of its own on the box.

    on_change(lines, moved) gets the new {name: value} each time; moved is None while a value is typed, else the
    dots changed: (old, new) for a renamed line, whose wires follow it, (old, "") for one taken away, ("", "")
    for one added (or a name that wasn't taken: the form shows the old one again)."""

    def __init__(self, lines: dict[str, Any], on_change: Callable[[dict[str, Any], tuple[str, str] | None], None],
                 hint: str = "") -> None:
        self._lines = dict(lines)
        self._on_change = on_change
        self._hint = hint

    def build(self) -> None:
        with ui.column().classes("w-full gap-1"):
            ui.label("values").classes("text-sm font-semibold")
            for name, value in self._lines.items():
                with ui.row().classes("items-center no-wrap w-full gap-2"):
                    ui.input("name", value=name).props("outlined dense").classes("w-32 shrink-0") \
                        .on("blur", lambda e, n=name: self._rename(n, e.sender.value))
                    ui.input("value", value="" if value is None else str(value),
                             on_change=lambda e, n=name: self._set(n, e.value)) \
                        .props("outlined dense").classes("flex-1 min-w-0")
                    ui.button(icon="close", on_click=lambda n=name: self._remove(n)) \
                        .props("flat round dense size=sm").tooltip("Take this value away (and its dot)")
            add = ui.button("Add value", icon="add", on_click=self._add).props("no-caps outline dense")
            add.classes("self-start")
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

    def _remove(self, name: str) -> None:
        self._lines.pop(name, None)
        self._on_change(dict(self._lines), (name, ""))
