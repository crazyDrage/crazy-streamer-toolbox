from collections.abc import Awaitable, Callable

from nicegui import ui

from streamer_toolbox.core.data.box_value import KINDS

FIELD = "outlined dense options-dense"


class SplitFieldsInput:
    """The outputs of a Split data box: one row per field with its kind. **Find fields** reads the data that is
    wired in and fills them by itself; a field can also be added by hand or taken away.

    on_change(fields) gets the new {field: kind}; find() fills them (the box's form is then built anew)."""

    def __init__(self, fields: dict[str, str], find: Callable[[], Awaitable[None]],
                 on_change: Callable[[dict[str, str]], None]) -> None:
        self._fields = dict(fields)
        self._find = find
        self._on_change = on_change

    def build(self) -> None:
        with ui.column().classes("w-full gap-1"):
            with ui.row().classes("items-center no-wrap w-full gap-2"):
                ui.label("outputs").classes("text-sm font-semibold flex-1")
                find = ui.button("Find fields", icon="auto_fix_high").props("no-caps flat dense")
                find.on_click(lambda: self._run_find(find))
            self._rows()
            ui.label("One output per field, as its kind. Find fields reads the data wired in (run the flow or "
                     "test the box before it first, if it isn't a Live value)").classes("text-xs opacity-60")

    def _rows(self) -> None:
        for name, kind in self._fields.items():
            with ui.row().classes("items-center no-wrap w-full gap-2"):
                ui.label(name).classes("text-sm flex-1 min-w-0 break-all")
                ui.select(list(KINDS), value=kind if kind in KINDS else "any",
                          on_change=lambda e, n=name: self._set(n, e.value)).props(FIELD).classes("w-28 shrink-0")
                ui.button(icon="close", on_click=lambda n=name: self._remove(n)) \
                    .props("flat round dense size=sm").tooltip("Take this output away")
        new = ui.input(placeholder="add a field by name").props("outlined dense").classes("w-full")
        new.on("keydown.enter", lambda: self._add(new.value))

    async def _run_find(self, button: ui.button) -> None:
        button.props("loading")
        try:
            await self._find()
        finally:
            button.props(remove="loading")

    def _set(self, name: str, kind: str) -> None:
        self._fields[name] = kind
        self._on_change(dict(self._fields))

    def _add(self, name: str) -> None:
        name = (name or "").strip()
        if name and name not in self._fields:
            self._fields[name] = "any"
            self._on_change(dict(self._fields))

    def _remove(self, name: str) -> None:
        self._fields.pop(name, None)
        self._on_change(dict(self._fields))
