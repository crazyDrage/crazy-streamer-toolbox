import uuid
from collections.abc import Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.widgets.field_list import KINDS, LIMITS, NUMBERS, FieldList

FIELD = "outlined dense options-dense"


class WidgetFieldsList:
    """The FIELDS tab as a list (his round 72: "a switch for FIELDS, to a list view with dropdown for options
    like type"): a card per setting with its name (what the code reads: {{name}}, fieldData.name), type, label,
    start value and group, and what its type has besides: min / max / step, a dropdown's choices, what a
    button sends. Up, delete, Add a setting. on_change(fields) after every change, with the whole FIELDS."""

    def __init__(self, fields: dict[str, dict[str, Any]], on_change: Callable[[dict[str, dict[str, Any]]], None]) \
            -> None:
        self._list = FieldList(fields)
        self._on_change = on_change
        self._new = ""  # a setting just added: scrolled into sight (it lands at the end of the list)
        self._id = f"fields_{uuid.uuid4().hex[:8]}"

    @ui.refreshable_method
    def build(self) -> None:
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            ui.label("Each setting is an input on the Settings tab. Its name is what the code reads: {{name}} in "
                     "HTML / CSS / JS, fieldData.name in JS.").classes("text-xs opacity-60 flex-1")
            # on top: the list scrolls, a button at its end would be out of sight
            with ui.dropdown_button("Add a setting", icon="add", auto_close=True) \
                    .props("no-caps outline dense").classes("shrink-0"):
                for kind, title in KINDS.items():
                    ui.item(title, on_click=lambda k=kind: self._add(k))
        if not self._list.fields:
            ui.label("No settings yet.").classes("text-sm opacity-70")
        for index, (name, spec) in enumerate(self._list.fields.items()):
            self._card(index, name, spec)
        if self._new:
            ui.run_javascript(f'document.getElementById("{self._id}")?.scrollIntoView({{block: "center"}})')
            self._new = ""

    def _card(self, index: int, name: str, spec: dict[str, Any]) -> None:
        kind = str(spec.get("type") or "text")
        card = ui.card().props("flat bordered").classes("w-full gap-1 p-2")
        if name == self._new:
            card.props(f"id={self._id}")
        with card:
            with ui.row().classes("items-center gap-2 w-full"):  # wraps on a phone
                box = ui.input("Name", value=name).props(FIELD).classes("flex-1 min-w-[10rem]") \
                    .tooltip("What the code reads: {{" + name + "}}, fieldData." + name)
                box.on("blur", lambda _, b=box: self._rename(name, b.value or ""))
                box.on("keydown.enter", lambda _, b=box: self._rename(name, b.value or ""))
                options = KINDS if kind in KINDS else {**KINDS, kind: kind}
                ui.select(options, value=kind, label="Type",
                          on_change=lambda e: self._change(lambda: self._list.set(name, "type", e.value), True)) \
                    .props(FIELD).classes("w-56 max-w-full")
                if index:
                    ui.button(icon="arrow_upward", on_click=lambda: self._change(lambda: self._list.up(name), True)) \
                        .props("flat round dense").tooltip("One place up (also on the Settings tab)")
                ui.button(icon="delete", on_click=lambda: self._change(lambda: self._list.remove(name), True)) \
                    .props("flat round dense").tooltip("Take this setting away")
            with ui.row().classes("items-center no-wrap gap-2 w-full"):
                self._text(name, "label", "Label", spec.get("label"), "flex-1 min-w-0")
                self._text(name, "group", "Group", spec.get("group"), "w-40 shrink-0",
                           "Settings with the same group are one section on the Settings tab")
            self._value(name, kind, spec)
            if kind in NUMBERS:
                with ui.row().classes("items-center no-wrap gap-2 w-full"):
                    for limit in LIMITS:
                        ui.number(limit.capitalize(), value=spec.get(limit),
                                  on_change=lambda e, part=limit: self._change(
                                      lambda: self._list.set(name, part, e.value))) \
                            .props(FIELD + " debounce=400").classes("flex-1 min-w-0")
            if kind == "dropdown":
                ui.textarea("Choices, one per line: value: what it shows",
                            value=FieldList.options_text(spec.get("options")),
                            on_change=lambda e: self._change(
                                lambda: self._list.set(name, "options", FieldList.options_from(e.value or "")))) \
                    .props(FIELD + " autogrow debounce=500").classes("w-full")

    def _value(self, name: str, kind: str, spec: dict[str, Any]) -> None:
        """The start value, with an input that fits the type."""
        value = spec.get("value")
        save = lambda v: self._change(lambda: self._list.set(name, "value", v))  # noqa: E731
        if kind == "checkbox":
            ui.switch("Starts on", value=bool(value), on_change=lambda e: save(e.value)).props("dense")
        elif kind in NUMBERS:
            ui.number("Start value", value=value if isinstance(value, (int, float)) else None,
                      on_change=lambda e: save(e.value)).props(FIELD + " debounce=400").classes("w-full")
        elif kind == "colorpicker":
            ui.color_input("Start colour", value=str(value or ""), on_change=lambda e: save(e.value or "")) \
                .props(FIELD).classes("w-full")
        elif kind == "dropdown" and isinstance(spec.get("options"), dict):
            ui.select(spec["options"], value=value if value in spec["options"] else None, label="Starts as",
                      on_change=lambda e: save(e.value)).props(FIELD).classes("w-full")
        else:
            label = "What it sends when pressed" if kind == "button" else "Start value"
            ui.input(label, value="" if value is None else str(value), on_change=lambda e: save(e.value or "")) \
                .props(FIELD + " debounce=400").classes("w-full")

    def _text(self, name: str, part: str, label: str, value: Any, classes: str, tip: str = "") -> None:
        box = ui.input(label, value="" if value is None else str(value),
                       on_change=lambda e: self._change(lambda: self._list.set(name, part, e.value or ""))) \
            .props(FIELD + " debounce=400").classes(classes)
        if tip:
            box.tooltip(tip)

    def _add(self, kind: str) -> None:
        self._new = self._list.add(kind)
        self._on_change(self._list.fields)
        self.build.refresh()

    def _rename(self, old: str, new: str) -> None:
        try:
            self._list.rename(old, new)
        except ValueError as e:
            ui.notify(str(e), type="warning", multi_line=True)
            self.build.refresh()  # back to the name it has
            return
        if new.strip() != old:
            self._on_change(self._list.fields)
            self.build.refresh()

    def _change(self, change: Callable[[], Any], redraw: bool = False) -> None:
        change()
        self._on_change(self._list.fields)
        if redraw:
            self.build.refresh()
