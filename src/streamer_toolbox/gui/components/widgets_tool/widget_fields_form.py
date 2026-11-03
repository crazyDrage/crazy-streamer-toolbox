from collections.abc import Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.files.file_types import AUDIO_TYPES, IMAGE_TYPES, VIDEO_TYPES
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.gui.components.file_dialog import FileDialog

FIELD = "outlined dense options-dense"
FILES = {"image-input": IMAGE_TYPES, "video-input": VIDEO_TYPES, "sound-input": AUDIO_TYPES}


class WidgetFieldsForm:
    """A widget's settings, drawn from its FIELDS like StreamElements' editor does: one input per field by its
    type (text, textarea, number, slider, checkbox, colorpicker, dropdown, googleFont; image / video / sound pick a file on
    this PC; a button sends its event), each group a section that opens and closes. on_change(values) after
    every change;
    on_button(field, value) when a button field is pressed."""

    def __init__(self, widget: Widget, on_change: Callable[[dict[str, Any]], None],
                 on_button: Callable[[str, Any], None]) -> None:
        self._fields = widget.fields
        self._values = dict(widget.field_data())
        self._on_change = on_change
        self._on_button = on_button

    def build(self) -> None:
        shown = {key: spec for key, spec in self._fields.items() if spec.get("type") != "hidden"}
        if not shown:
            ui.label("This widget has no settings (its FIELDS part is empty).").classes("text-sm opacity-70")
            return
        groups: dict[str, dict[str, dict[str, Any]]] = {}
        for key, spec in shown.items():
            groups.setdefault(str(spec.get("group") or ""), {})[key] = spec
        for number, (group, fields) in enumerate(groups.items()):
            if not group:  # fields without a group: just there
                for key, spec in fields.items():
                    self._field(key, spec)
                continue
            # a group opens and closes, like in StreamElements' editor; the first one starts open
            with ui.expansion(group, value=number == 0).props("dense expand-separator") \
                    .classes("w-full border border-gray-500/30 rounded"):
                with ui.column().classes("w-full gap-2"):
                    for key, spec in fields.items():
                        self._field(key, spec)

    def _field(self, key: str, spec: dict[str, Any]) -> None:
        kind, label, value = spec.get("type", "text"), str(spec.get("label") or key), self._values.get(key)
        limits = {name: spec[name] for name in ("min", "max", "step") if isinstance(spec.get(name), (int, float))}
        if kind == "button":
            ui.button(label, on_click=lambda: self._on_button(key, spec.get("value", ""))) \
                .props("no-caps outline dense")
        elif kind == "checkbox":
            ui.switch(label, value=bool(value), on_change=lambda e: self._set(key, e.value)).props("dense")
        elif kind == "number":
            ui.number(label, value=value if isinstance(value, (int, float)) else None, **limits,
                      on_change=lambda e: self._set(key, e.value)).props(FIELD + " debounce=500").classes("w-full")
        elif kind == "slider":
            # his round 74: the number on the left, to type it in; both show the same value
            ui.label(label).classes("text-sm")
            start = value if isinstance(value, (int, float)) else limits.get("min", 0)
            with ui.row().classes("items-center no-wrap gap-3 w-full"):
                typed = ui.number(value=start, min=limits.get("min", 0), max=limits.get("max", 100),
                                  step=limits.get("step", 1)).props(FIELD + " debounce=500").classes("w-24 shrink-0")
                slider = ui.slider(value=start, min=limits.get("min", 0), max=limits.get("max", 100),
                                   step=limits.get("step", 1)).props("label").classes("flex-1")
            slider.on("change", lambda e: (typed.set_value(e.args), self._set(key, e.args)))

            def typed_in(number: Any) -> None:
                if not isinstance(number, (int, float)):
                    return
                low, high = limits.get("min", 0), limits.get("max", 100)
                kept = min(max(number, low), high)  # a typed number stays on the slider (64100 was saved)
                if kept != number:
                    typed.set_value(kept)
                    return  # set_value comes back here with the kept number
                if kept != slider.value:
                    slider.set_value(kept)
                    self._set(key, kept)

            typed.on_value_change(lambda e: typed_in(e.value))
        elif kind == "colorpicker":
            ui.color_input(label, value=str(value or ""), on_change=lambda e: self._set(key, e.value or "")) \
                .props(FIELD).classes("w-full")
        elif kind == "dropdown" and isinstance(spec.get("options"), dict):
            options = {**spec["options"], **({value: str(value)} if value not in spec["options"] and value else {})}
            ui.select(options, value=value if value in options else None, label=label,
                      on_change=lambda e: self._set(key, e.value)).props(FIELD).classes("w-full")
        elif kind in FILES:
            self._file(key, label, str(value or ""), FILES[kind])
        elif kind == "textarea":  # the toolbox's own kind: a text of several lines (an Element's texts)
            ui.textarea(label, value="" if value is None else str(value),
                        on_change=lambda e: self._set(key, e.value or "")) \
                .props(FIELD + " autogrow debounce=500").classes("w-full")
        else:  # text, googleFont, and kinds this form doesn't know: plain text
            ui.input(label, value="" if value is None else str(value),
                     on_change=lambda e: self._set(key, e.value)).props(FIELD + " debounce=500").classes("w-full")

    def _file(self, key: str, label: str, value: str, endings: tuple[str, ...]) -> None:
        with ui.row().classes("items-center no-wrap gap-1 w-full"):
            box = ui.input(label, value=value, on_change=lambda e: self._set(key, (e.value or "").strip())) \
                .props(FIELD + " clearable debounce=500").classes("flex-1 min-w-0")

            async def pick() -> None:
                path = await FileDialog(endings).open(box.value or "")
                if path:
                    box.set_value(path)

            ui.button(icon="folder_open", on_click=pick).props("flat round dense").tooltip("Pick a file on this PC")

    def _set(self, key: str, value: Any) -> None:
        self._values[key] = _whole(value)
        self._on_change(dict(self._values))


def _whole(value: Any) -> Any:
    """10.0 → 10: a number input gives floats, and {{size}}px in the code should read 10px, not 10.0px."""
    return int(value) if isinstance(value, float) and value.is_integer() else value
