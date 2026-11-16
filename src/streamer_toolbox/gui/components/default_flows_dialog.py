from pathlib import Path

from nicegui import ui

from streamer_toolbox.core.event_types.event_flows import EventFlows
from streamer_toolbox.core.flows.default_flows import DefaultFlows
from streamer_toolbox.core.flows.flow_pack import FlowPack

UPDATE_NOTE = "There already: tick it to update it to the default"


class DefaultFlowsDialog:
    """The window behind "Add default flows" (his round 76): every flow of the file with a tick, and (his 11-14)
    the connection's event types with their own flows (Overlay → Events), Select all / Deselect all, Add for the
    ticked ones. New ones come ticked. One there already comes unticked; ticking it updates it to the default,
    after a popup that names them (his "make an popup for updating the existing flows with the same name")."""

    def __init__(self, default_flows: DefaultFlows, file: Path, event_flows: EventFlows | None = None,
                 events: tuple[str, ...] = ()) -> None:
        self._default_flows = default_flows
        self._file = file
        self._event_flows = event_flows
        self._events = events if event_flows is not None else ()

    async def ask_and_add(self) -> list[str]:
        """Opens the window; gives the labels it added or updated (empty when he cancelled or picked nothing)."""
        pack = FlowPack.from_text(self._file.read_text(encoding="utf-8"))
        there = self._default_flows.there(self._file)
        flow_boxes: dict[str, tuple[ui.checkbox, bool]] = {}  # label → (its tick, there already)
        event_boxes: dict[str, tuple[ui.checkbox, bool]] = {}  # event → (its tick, its flow there already)
        with ui.dialog() as dialog, ui.card().classes("w-[40rem] max-w-full gap-3"):
            ui.label("Add default flows").classes("text-lg font-semibold")
            with ui.row().classes("gap-2"):
                ui.button("Select all", icon="done_all",
                          on_click=lambda: self._tick_all(flow_boxes, event_boxes, value=True)) \
                    .props("flat dense no-caps")
                ui.button("Deselect all", icon="remove_done",
                          on_click=lambda: self._tick_all(flow_boxes, event_boxes, value=False)) \
                    .props("flat dense no-caps")
            with ui.column().classes("w-full gap-2 max-h-[60vh] overflow-y-auto"):
                ui.label(f'Flows: into the folder "{pack.folder}", new ones switched off') \
                    .classes("text-sm font-semibold")
                for flow in pack.flows:
                    is_there = flow.label.casefold() in there
                    flow_boxes[flow.label] = (self._row(flow.label, flow.description, is_there), is_there)
                if self._events:
                    ui.label("Events (Overlay → Events) with the flow that sends each one to your widgets and "
                             "alerts").classes("text-sm font-semibold mt-2")
                    for event in self._events:
                        own = self._event_flows.own_flow(event)
                        if own is None:
                            note = "the event type and its flow"
                        else:  # only when another flow of his sends it
                            note = "" if own.label == f"Event: {event}" else f'Sent by your flow "{own.label}"'
                        event_boxes[event] = (self._row(f"Event: {event}", note, own is not None), own is not None)
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Add", icon="playlist_add", on_click=lambda: dialog.submit(True)).props("unelevated no-caps")
        go = await dialog
        dialog.delete()
        if not go:
            return []
        flows = {label: is_there for label, (box, is_there) in flow_boxes.items() if box.value}
        events = {event: is_there for event, (box, is_there) in event_boxes.items() if box.value}
        if not flows and not events:
            ui.notify("Nothing picked, nothing added", type="info")
            return []
        existing = [label for label, is_there in flows.items() if is_there] + \
                   [f"Event: {event}" for event, is_there in events.items() if is_there]
        update = True
        if existing:
            update = await self._ask_update(existing)
            if update is None:
                return []
        return self._do(flows, events, update)

    def _do(self, flows: dict[str, bool], events: dict[str, bool], update: bool) -> list[str]:
        added, _ = self._default_flows.add(self._file, only={label for label, there in flows.items() if not there})
        updated = self._default_flows.update(self._file, [label for label, there in flows.items() if there]) \
            if update else []
        for event, is_there in events.items():
            if not is_there and self._event_flows.add_default(event):
                added.append(f"Event: {event}")
            elif is_there and update and self._event_flows.update_default(event):
                updated.append(f"Event: {event}")
        lines = [f"{what}: {', '.join(labels)}" for what, labels in (("Added", added), ("Updated", updated)) if labels]
        ui.notify(" · ".join(lines) or "Nothing new", type="positive" if lines else "info", multi_line=True)
        return added + updated

    @staticmethod
    def _row(label: str, note: str, is_there: bool) -> ui.checkbox:
        with ui.row().classes("w-full no-wrap items-start gap-1"):
            box = ui.checkbox(value=not is_there).props("dense").classes("mt-1")
            with ui.column().classes("gap-0 min-w-0"):
                ui.label(label).classes("font-medium")
                if is_there:
                    ui.label(UPDATE_NOTE).classes("text-xs text-warning")
                if note:
                    ui.label(note).classes("text-xs opacity-60")
        return box

    @staticmethod
    async def _ask_update(existing: list[str]) -> bool | None:
        """True: update them; False: only add the new ones; None: cancelled."""
        with ui.dialog() as dialog, ui.card().classes("w-[30rem] max-w-full gap-3"):
            ui.label(f"Update {len(existing)} flow{'s' if len(existing) > 1 else ''} that you have already?") \
                .classes("text-lg font-semibold")
            ui.label("They become the default again: your changes to them are lost. Each keeps its on/off.") \
                .classes("text-sm opacity-80")
            with ui.column().classes("gap-0 max-h-[30vh] overflow-y-auto"):
                for label in existing:
                    ui.label(f"• {label}").classes("text-sm")
            with ui.row().classes("w-full justify-end gap-2 flex-wrap"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Only add the new ones", on_click=lambda: dialog.submit(False)).props("outline no-caps")
                ui.button("Update them", icon="sync", on_click=lambda: dialog.submit(True)) \
                    .props("unelevated no-caps color=warning")
        answer = await dialog
        dialog.delete()
        return answer

    @staticmethod
    def _tick_all(*groups: dict[str, tuple[ui.checkbox, bool]], value: bool = True) -> None:
        for group in groups:
            for box, _ in group.values():
                box.value = value
