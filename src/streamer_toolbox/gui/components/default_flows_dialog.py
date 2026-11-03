from pathlib import Path

from nicegui import ui

from streamer_toolbox.core.flows.default_flows import DefaultFlows
from streamer_toolbox.core.flows.flow_pack import FlowPack


class DefaultFlowsDialog:
    """The window behind "Add default flows" (his round 76): every flow of the file with a tick, Select all /
    Deselect all, and Add for the ticked ones. Flows already in the folder show greyed out, without a tick."""

    def __init__(self, default_flows: DefaultFlows, file: Path) -> None:
        self._default_flows = default_flows
        self._file = file

    async def ask_and_add(self) -> list[str]:
        """Opens the window; gives the labels it added (empty when he cancelled or nothing was new)."""
        pack = FlowPack.from_text(self._file.read_text(encoding="utf-8"))
        there = self._default_flows.there(self._file)
        boxes: dict[str, ui.checkbox] = {}
        with ui.dialog() as dialog, ui.card().classes("w-[40rem] max-w-full gap-3"):
            ui.label("Add default flows").classes("text-lg font-semibold")
            ui.label(f'Into the folder "{pack.folder}", switched off.').classes("text-sm opacity-80")
            with ui.row().classes("gap-2"):
                ui.button("Select all", icon="done_all",
                          on_click=lambda: self._tick_all(boxes, True)).props("flat dense no-caps")
                ui.button("Deselect all", icon="remove_done",
                          on_click=lambda: self._tick_all(boxes, False)).props("flat dense no-caps")
            with ui.column().classes("w-full gap-2 max-h-[60vh] overflow-y-auto"):
                for flow in pack.flows:
                    is_there = flow.label.casefold() in there
                    with ui.row().classes("w-full no-wrap items-start gap-1"):
                        box = ui.checkbox(value=not is_there).props("dense").classes("mt-1")
                        with ui.column().classes("gap-0 min-w-0"):
                            ui.label(flow.label).classes("font-medium")
                            if is_there:
                                ui.label("In the folder already").classes("text-xs text-positive")
                            if flow.description:
                                ui.label(flow.description).classes("text-xs opacity-60")
                    if is_there:
                        box.disable()
                        box.classes("opacity-50")
                    else:
                        boxes[flow.label] = box
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Add", icon="playlist_add",
                          on_click=lambda: dialog.submit({label for label, b in boxes.items() if b.value})) \
                    .props("unelevated no-caps")
        picked = await dialog
        dialog.delete()
        if not picked:
            if picked is not None:
                ui.notify("Nothing picked, nothing added", type="info")
            return []
        added, _there = self._default_flows.add(self._file, only=picked)
        ui.notify(f'Added to "{pack.folder}" (off): ' + ", ".join(added), type="positive", multi_line=True)
        return added

    @staticmethod
    def _tick_all(boxes: dict[str, ui.checkbox], value: bool) -> None:
        for box in boxes.values():
            box.value = value
