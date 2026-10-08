import json
from typing import Any

from nicegui import ui

from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.variables.variable_store import VariableStore


class VariablesPage:
    """Every variable with its value: add, change, rename (the flows that use it are changed too), delete. Values
    update by themselves when a flow sets them."""

    def __init__(self, variables: VariableStore, flows: FlowLibrary) -> None:
        self._variables = variables
        self._flows = flows

    def build(self) -> None:
        ui.label("Flows save values here (\"Save result in variable\" or the Set variable box) and read them back "
                 "in any box field (source: Variable). They're kept in a file, so they survive a restart.") \
            .classes("text-sm opacity-80")
        with ui.row().classes("items-center gap-2"):
            ui.button("New variable", icon="add", on_click=lambda: self._edit("", "")).props("no-caps unelevated")
            search = ui.input(placeholder="Search").props("dense clearable").classes("w-60")
        shown = {"values": None}

        @ui.refreshable
        def table() -> None:
            values = self._variables.all()
            shown["values"] = values
            wanted = (search.value or "").casefold()
            rows = [(name, value) for name, value in values.items()
                    if wanted in name.casefold() or wanted in json.dumps(value).casefold()]
            if not rows:
                ui.label("No variables yet." if not values else "Nothing matches.").classes("opacity-70")
            with ui.column().classes("w-full gap-2"):
                for name, value in rows:
                    with ui.card().classes("w-full p-3"):
                        with ui.row().classes("items-start no-wrap gap-3 w-full"):
                            with ui.column().classes("gap-0 min-w-0 flex-1"):
                                ui.label(name).classes("font-semibold break-all")
                                ui.label(_type(value)).classes("text-xs opacity-60")
                            ui.code(json.dumps(value, indent=1, ensure_ascii=False), language="json") \
                                .classes("flex-[2] min-w-0 text-xs")
                            ui.button(icon="edit", on_click=lambda n=name, v=value: self._edit(n, v)) \
                                .props("flat round dense").tooltip("Change")
                            ui.button(icon="delete", on_click=lambda n=name: self._delete(n)) \
                                .props("flat round dense").tooltip("Delete")

        table()
        search.on_value_change(table.refresh)

        def refresh_if_changed() -> None:
            if shown["values"] != self._variables.all():
                table.refresh()

        ui.timer(1.0, refresh_if_changed)

    async def _edit(self, name: str, value: Any) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-[32rem] max-w-full gap-3"):
            ui.label("Change variable" if name else "New variable").classes("text-lg font-semibold")
            name_input = ui.input("Name", value=name).classes("w-full").props("autofocus" if not name else "")
            text = value if isinstance(value, str) else json.dumps(value, indent=1, ensure_ascii=False)
            value_input = ui.textarea("Value", value=text).props("autogrow").classes("w-full font-mono")
            ui.label("Text, a number, true/false, or JSON like {\"x\": 0.5, \"y\": -1}").classes("text-xs opacity-60")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("no-caps flat")
                ui.button("Save", icon="save", on_click=lambda: dialog.submit((name_input.value.strip(),
                                                                                 value_input.value))) \
                    .props("no-caps unelevated")
        result = await dialog
        dialog.delete()
        if not result:
            return
        new_name, raw = result
        if new_name != name and new_name in self._variables.names():
            ui.notify(f"There already is a variable {new_name}: pick another name or change that one",
                      type="warning")
            return
        try:
            self._variables.set(new_name, _parse(raw))
        except Exception as e:
            ui.notify(f"Not saved: {e}", type="negative")
            return
        if name and new_name != name:
            self._variables.delete(name)
            changed = self._flows.rename_variable(name, new_name)
            ui.notify(f"Renamed to {new_name}" + (f"; changed in: {', '.join(changed)}" if changed else
                                                   "; no flow used it"), type="positive", multi_line=True)
            return
        ui.notify(f"{new_name} saved", type="positive")

    def _delete(self, name: str) -> None:
        self._variables.delete(name)
        ui.notify(f"{name} deleted")


def _parse(raw: str) -> Any:
    """JSON if it reads as JSON (numbers, true/false, objects), else the text itself."""
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def _type(value: Any) -> str:
    if isinstance(value, bool):
        return "true/false"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, dict):
        return "object: " + ", ".join(value)
    if isinstance(value, list):
        return f"list of {len(value)}"
    return "text"
