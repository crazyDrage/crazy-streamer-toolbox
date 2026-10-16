import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.data.kind_check import KindCheck
from streamer_toolbox.core.actions.registered_action import OptionsProvider
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.files.file_types import FOLDER
from streamer_toolbox.core.flows.box_wire import WIRE_IN, box_source, is_wire_in
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.gui.components.file_dialog import FileDialog
from streamer_toolbox.gui.components.flow_editor.many_picker import Light, ManyPicker
from streamer_toolbox.gui.components.keep_typed import keep_typed

VAR = re.compile(r"\$\{var\.(\w+)((?:\.\w+)*)\}")
INPUT = re.compile(r"\$\{input\.(\w+)\}")
LIVE = re.compile(r"\$\{get\.(\w+\.\w+)((?:\.\w+)*)\}")
SOURCES = {"value": "Value", "var": "Variable", "get": "Live value", "input": "Flow input", "box": "Wire from a box"}
FIELD = "outlined dense options-dense"

LiveReader = Callable[[str], Awaitable[Any]]


class ParamInput:
    """One parameter of a box, as one block: its name and where the value comes from on one line, the field below,
    one small hint line under it. The value is typed (or picked from the service's list), a variable (optionally one
    field of it, e.g. x of a position), a Live value (read from a service when the box runs, e.g. the loaded VTS
    model), one of the flow's inputs or a wire from another box (onto the field's dot on the box's left). While a
    wire is on it, the block shows only the wire and a button to take it away. Stored as
    the value or as ${var.name.field} / ${get.action.field} / ${input.name} / ${box.n3.field} (${box} = not wired
    yet), so the flow file stays readable. on_change(value, rebuild) says when the box's dots change."""

    def __init__(self, name: str, default: Any, value: Any, annotation: Any, options: OptionsProvider | None,
                 variables: VariableStore, flow_inputs: list[str], live: dict[str, str], read_live: LiveReader,
                 wire_sources: dict[str, str], on_change: Callable[[Any, bool], None], warning: str = "",
                 label: str = "", hint: str = "", files: tuple[str, ...] | None = None, color: bool = False,
                 many: OptionsProvider | None = None, light: Light | None = None) -> None:
        self._name = name
        self._label = label or field_label(name)
        self._hint = hint
        self._files = files  # the field holds a file on this PC: the endings it takes (see RegisteredAction.files)
        self._color = color  # the field holds a colour: a colour picker next to it
        self._many = many  # the field takes several of this list: a window to tick them in
        self._light = light  # that window can light the one under the mouse up in the program
        self._default = default
        self._value = value
        self._annotation = annotation = KindCheck.plain(annotation)
        self._options = options
        self._variables = variables
        self._flow_inputs = flow_inputs
        self._live = live
        self._read_live = read_live
        self._wire_sources = wire_sources
        self._warning = warning  # the wire brings the wrong kind
        self._on_change = on_change
        text = value if isinstance(value, str) else ""
        self._source = "box" if is_wire_in(value) else next(
            (s for s, pattern in (("var", VAR), ("get", LIVE), ("input", INPUT)) if pattern.fullmatch(text)), "value")
        if value in ("", None) and annotation in (dict, "dict"):  # a position etc. comes from a variable
            self._source = "var"

    def build(self) -> None:
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("items-center no-wrap w-full gap-2"):
                ui.label(self._label).classes("text-sm font-semibold flex-1 min-w-0")
                if box_source(self._value):  # wired: its other settings come back when the wire is gone
                    ui.button("Remove wire", icon="link_off", on_click=lambda: self._switch("value")) \
                        .props("flat dense no-caps size=sm") \
                        .tooltip("Takes the wire away: then the field can be typed or picked again")
                else:
                    sources = SOURCES if self._live or self._source == "get" else \
                        {k: v for k, v in SOURCES.items() if k != "get"}
                    ui.select(sources, value=self._source, on_change=lambda e: self._switch(e.value)) \
                        .props("dense options-dense borderless").classes("w-32 shrink-0 text-xs")
            if self._hint:
                ui.label(self._hint).classes("text-xs opacity-70 -mt-1")
            self._body()

    @ui.refreshable_method
    def _body(self) -> None:
        if self._source == "var":
            self._variable()
        elif self._source == "get":
            self._live_value()
        elif self._source == "input":
            match = INPUT.fullmatch(str(self._value))
            ui.select(self._flow_inputs, value=match.group(1) if match else None, label="flow input",
                      on_change=lambda e: self._set(f"${{input.{e.value}}}" if e.value else "")) \
                .props(FIELD).classes("w-full")
            _hint("" if self._flow_inputs else "Add inputs at the top of the page (Inputs) first")
        elif self._source == "box":
            self._wire()
        else:
            self._plain()

    def _variable(self) -> None:
        match = VAR.fullmatch(str(self._value))
        name, field = (match.group(1), match.group(2).lstrip(".")) if match else (None, "")
        names = sorted(set(self._variables.names()) | ({name} if name else set()), key=str.casefold)
        current = self._variables.get(name) if name else None
        with ui.row().classes("no-wrap gap-2 w-full"):
            pick = keep_typed(ui.select(names, value=name, label="variable", new_value_mode="add-unique")
                              .props(FIELD).classes("flex-1 min-w-0"))
            part = _field_picker(current, field)

        def changed() -> None:
            if pick.value:
                chosen = (part.value or "").strip() if part else ""
                self._set(f"${{var.{pick.value}{'.' + chosen if chosen else ''}}}")
                if part is None and isinstance(self._variables.get(pick.value), dict):
                    self._body.refresh()  # an object: offer its fields

        pick.on_value_change(changed)
        if part:
            part.on_value_change(changed)
        if name and name in self._variables.names():
            shown = current.get(field, current) if field and isinstance(current, dict) else current
            _hint(f"now: {_short(shown)}")

    def _wire(self) -> None:
        wired = self._value if box_source(self._value) else None
        choices = dict(self._wire_sources) | ({wired: wired} if wired and wired not in self._wire_sources else {})
        ui.select(choices, value=wired, label="from box",
                  on_change=lambda e: self._set(e.value or WIRE_IN, rebuild=True)).props(FIELD).classes("w-full")
        if wired and self._warning:
            ui.label(f"⚠ {self._warning}: it may fail when the box runs").classes("text-xs text-warning")
        where = f"this box's orange '{self._label}' dot"
        ui.label(f"Or drag a wire from another box's orange dot to {where}. A box with no run wire into it runs "
              "whenever its value is needed" if wired else f"Not wired yet: drag a wire from another box's orange "
              f"dot to {where}, or pick the box here").classes("text-xs opacity-60")

    def _live_value(self) -> None:
        match = LIVE.fullmatch(str(self._value))
        action, field = (match.group(1), match.group(2).lstrip(".")) if match else (None, "")
        choices = dict(self._live) | ({action: action} if action and action not in self._live else {})
        with ui.row().classes("no-wrap gap-2 w-full") as row:
            pick = ui.select(choices, value=action, label="read from").props(FIELD).classes("flex-1 min-w-0")
        hint = _hint("Read when the box runs, so it's always up to date")

        def changed(part: Any = None) -> None:
            if pick.value:
                chosen = (part.value or "").strip() if part is not None else field
                self._set(f"${{get.{pick.value}{'.' + chosen if chosen else ''}}}")

        async def preview() -> None:
            """Reads it once now, to show the value and offer the fields of an object (a position)."""
            if not pick.value:
                return
            try:
                now = await self._read_live(pick.value)
            except Exception as e:  # service not connected: the box still works once it is
                hint.set_text(f"can't read it now: {e}")
                return
            if isinstance(now, dict):
                with row:
                    part = _field_picker(now, field)
                part.on_value_change(lambda: changed(part))
            hint.set_text(f"now: {_short(now)}")

        pick.on_value_change(lambda: (changed(), self._body.refresh()))
        ui.timer(0.1, preview, once=True)

    def _plain(self) -> None:
        value = "" if self._value is None else self._value  # may hold text like "hi ${event.user}"
        if isinstance(value, (dict, list)):  # an object / list typed into the flow file: edit it as JSON
            value = json.dumps(value, ensure_ascii=False)
        default = f"default: {self._default}" if self._default not in (None, "") else ""

        def changed(e) -> None:
            self._set(_coerce(e.value, self._annotation))

        yes_no = isinstance(value, bool) or str(value).strip().casefold() in ("", "true", "false")
        if self._annotation in (bool, "bool") and yes_no:  # on / off; text like "${event.x}" keeps the text field
            on = to_bool(value) if value != "" else bool(self._default)
            ui.switch("on" if on else "off", value=on,
                      on_change=lambda e: (self._set(e.value), e.sender.set_text("on" if e.value else "off")))
            return
        if self._options is None:
            with ui.row().classes("no-wrap items-center gap-1 w-full"):
                field = ui.input(value=str(value), placeholder=default, on_change=changed).props(FIELD) \
                    .classes("flex-1 min-w-0")
                self._file_button(field.set_value)
                self._color_button(field.set_value)
                self._many_button(field.set_value)
            return
        current = [str(value)] if value not in ("", None) else []
        with ui.row().classes("no-wrap gap-2 w-full") as row:
            select = ui.select(current, value=str(value) if current else None, label=default or "pick or type",
                               new_value_mode="add-unique", on_change=changed).props(FIELD).classes("flex-1 min-w-0")
            keep_typed(select)
            self._file_button(lambda path: (select.set_options(_sorted(select.options, [path])),
                                            select.set_value(path)))
            self._color_button(lambda color: (select.set_options(_sorted(select.options, [color])),
                                              select.set_value(color)))
        hint = _hint("")

        async def load() -> None:
            try:
                choices = await self._options()
            except Exception as e:  # service not connected: typing still works
                hint.set_text(f"list not available: {e}")
                return
            if isinstance(choices, dict) and choices and all(isinstance(v, dict) for v in choices.values()):
                self._grouped(row, select, choices, current)
                return
            labels = dict(choices) if isinstance(choices, dict) else {c: c for c in choices}
            select.set_options(_sorted(labels, current), value=select.value)

        ui.timer(0.1, load, once=True)

    def _file_button(self, use: Callable[[str], Any]) -> None:
        """A file field's button: opens the file window where the value is; the pick goes into the field."""
        if self._files is None:
            return

        async def pick() -> None:
            path = await FileDialog(self._files).open(self._value if isinstance(self._value, str) else "")
            if path:
                use(path)

        ui.button(icon="folder_open", on_click=pick).props("flat round dense") \
            .tooltip("Pick a folder on this PC" if self._files == FOLDER else "Pick a file on this PC")

    def _color_button(self, use: Callable[[str], Any]) -> None:
        """A colour field's button: a colour picker with alpha (how see-through); the pick goes into the field
        as hex, #FF8800, or #FF880080 when it isn't fully solid."""
        if not self._color:
            return
        now = self._value if isinstance(self._value, str) and self._value.startswith("#") else ""

        def picked(e) -> None:
            color = e.color.upper()
            use(color[:7] if len(color) == 9 and color.endswith("FF") else color)
            button.style(f"color: {color[:7]}")

        with ui.button(icon="palette").props("flat round dense").tooltip("Pick a colour") as button:
            picker = ui.color_picker(on_pick=picked)
            picker.q_color.props("format-model=hexa")  # hexa: the picker shows its alpha slider
            picker.set_color(now if len(now) == 9 else f"{now}FF" if len(now) == 7 else "#FFFFFFFF")
        if now:
            button.style(f"color: {now[:7]}")

    def _many_button(self, use: Callable[[str], Any]) -> None:
        """The button of a field that takes several of a list: a window to tick them in."""
        if self._many is None:
            return

        async def pick() -> None:
            try:
                choices = list(await self._many())
            except Exception as e:  # service not connected: typing still works
                ui.notify(f"The list isn't available: {e}", type="warning")
                return
            chosen = [part.strip() for part in str(self._value or "").split(",") if part.strip()]
            picked = await ManyPicker(choices, chosen, self._light).pick(self._label)
            if picked is not None:
                use(", ".join(picked))

        ui.button(icon="checklist", on_click=pick).props("flat round dense").tooltip("Pick from the list")

    @staticmethod
    def _grouped(row: ui.row, select: ui.select, groups: dict[str, dict[str, str]], current: list[str]) -> None:
        """A list in groups (SAMMI buttons by deck, OBS requests by category): a group picker in front narrows the
        list. It starts at the group of the value that's set; "all" shows every group, each label with its group."""
        everything = {value: f"{label} · {group}" for group, items in groups.items() for value, label in items.items()}
        start = next((g for g, items in groups.items() if current and current[0] in items), ALL)

        def show(group: str) -> None:
            items = dict(everything if group == ALL else groups.get(group, {}))
            if select.value and select.value not in items and select.value in everything:
                items[select.value] = everything[select.value]  # the chosen one, from another group
            select.set_options(_sorted(items, current), value=select.value)

        with row:
            pick = ui.select([ALL] + sorted(groups, key=str.casefold), value=start, label="group",
                             on_change=lambda e: show(e.value)).props(FIELD).classes("w-36 shrink-0")
        pick.move(target_index=0)
        show(start)

    def _switch(self, source: str) -> None:
        dots_change = "box" in (source, self._source)
        self._source = source
        self._set(WIRE_IN if source == "box" else "", rebuild=dots_change)
        if not dots_change:
            self._body.refresh()

    def _set(self, value: Any, rebuild: bool = False) -> None:
        self._value = value
        self._on_change(value, rebuild)


ALL = "all"  # the group picker's "every group" choice


SORT_ABOVE = 12  # longer lists (scenes, SAMMI buttons) are sorted A-Z; shorter ones keep the order given


def _sorted(labels: dict[str, str] | list[str], current: list[str]) -> dict[str, str]:
    """Choices in the order the box gives them (e.g. Nothing, Start over, Add time), a long list A-Z so it's easy
    to find something; a typed or old value stays pickable even if it isn't in the list."""
    labels = dict(labels) if isinstance(labels, dict) else {c: c for c in labels}
    labels |= {c: c for c in current if c not in labels}
    if len(labels) <= SORT_ABOVE:
        return labels
    return dict(sorted(labels.items(), key=lambda item: str(item[1]).casefold()))


def field_label(name: str) -> str:
    """A field's name as words: "if_started_again" → "If started again", "case_1" → "Case 1"."""
    words = name.replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def _field_picker(value: Any, field: str) -> ui.select | None:
    """A field of an object (x of a position); nothing for a plain value unless a field was already set."""
    if not isinstance(value, dict) and not field:
        return None
    fields = sorted((set(value) if isinstance(value, dict) else set()) | ({field} if field else set()))
    return keep_typed(ui.select(fields, value=field or None, label="field", clearable=True,
                                new_value_mode="add-unique").props(FIELD).classes("w-28 shrink-0"))


def _hint(text: str) -> ui.label:
    return ui.label(text).classes("text-xs opacity-60 break-all")


def _coerce(value: Any, annotation: Any) -> Any:
    """Typed text to the parameter's type (1.5 for a float)."""
    if not isinstance(value, str) or value.strip() == "":
        return value
    for kind in (int, float):
        if annotation in (kind, kind.__name__):
            try:
                return kind(value)
            except ValueError:
                return value
    if annotation in (bool, "bool"):
        return value.strip().casefold() in ("1", "true", "yes", "on")
    return value


def _short(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{k} = {round(v, 3) if isinstance(v, float) else v}" for k, v in value.items())
    return str(value)[:80]
