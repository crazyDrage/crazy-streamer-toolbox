from collections.abc import Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.gui.components.flow_editor.wire_matcher import WireMatcher


class WireByNameDialog:
    """The list for "Wire by name": one row per field of the box that has a same-named orange output somewhere,
    ticked where it's clear which one. Apply sets the ticked fields to those wires."""

    def __init__(self, fields: list[str], sources: dict[str, str], current: dict[str, Any],
                 apply: Callable[[dict[str, str]], None]) -> None:
        self._rows = WireMatcher.candidates(fields, sources, current)
        self._apply = apply

    def open(self) -> None:
        if not self._rows:
            ui.notify("No other box has an output with the same name as one of this box's fields", type="info")
            return
        picks: dict[str, str | None] = {field: pick for field, _, pick in self._rows}
        with ui.dialog() as dialog, ui.card().classes("w-[440px] max-w-[95vw] gap-2"):
            ui.label("Wire by name").classes("text-lg font-semibold")
            ui.label("Fields of this box with an orange output of the same name. Tick the ones to wire.") \
                .classes("text-sm opacity-80")
            for field, matches, pick in self._rows:
                with ui.row().classes("items-center no-wrap w-full gap-2"):
                    ui.label(field.replace("_", " ")).classes("w-24 shrink-0 text-sm font-semibold")
                    ui.select({"": "leave as it is"} | matches, value=pick or "",
                              on_change=lambda e, f=field: picks.__setitem__(f, e.value or None)) \
                        .props("dense outlined options-dense").classes("flex-1 min-w-0")

            def apply() -> None:
                chosen = {field: ref for field, ref in picks.items() if ref}
                dialog.close()
                if chosen:
                    self._apply(chosen)
                    ui.notify(f"Wired {len(chosen)}: {', '.join(chosen)}", type="positive")

            with ui.row().classes("w-full justify-end gap-2 pt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
                ui.button("Wire them", icon="cable", on_click=apply).props("unelevated no-caps")
        dialog.open()
