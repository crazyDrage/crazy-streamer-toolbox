from collections.abc import Awaitable, Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.widgets.element_design import LIST_ANIMATIONS, LIST_EVENTS, NEWEST, ElementDesign
from streamer_toolbox.gui.components.widgets_tool.entry_table_dialog import EntryTableDialog

FIELD = "outlined dense options-dense"

# change(key, what, whole=..., group=...): WidgetDesigner._change
Change = Callable[..., None]


class DesignListPanel:
    """The settings of an event list (the widget editor's "Event list" piece, his round 89): which events it
    shows, each with its own look (EntryTableDialog), how many it keeps, the space between them, where new ones
    come in, how they come in, whether they go after some seconds, whether OBS shows the last ones again after
    it loads the widget. Its biggest size is the piece's width and height.
    Part of DesignPiecePanel."""

    def __init__(self, design: ElementDesign, layer: int, name: str, change: Change, windows: ui.element,
                 take_file: Callable[[str, bytes], str | None], media: Callable[[str], str],
                 pick_file: Callable[[tuple[str, ...]], Awaitable[tuple[str, bytes] | None]],
                 values: Callable[[str], list[dict[str, Any]]]) -> None:
        self._design = design
        self._layer = layer
        self._name = name
        self._change = change
        self._windows = windows
        self._take_file = take_file
        self._media = media
        self._pick_file = pick_file
        self._values = values  # an event's values (WidgetDesigner._list_values)

    def build(self) -> None:
        now = self._design.event_list(self._layer, self._name)
        ui.label("The events").classes("text-sm font-semibold pt-1")
        if not now["entries"]:
            ui.label("None yet: add one below.").classes("text-sm opacity-70")
        for entry in now["entries"]:
            event = entry["event"]
            with ui.row().classes("w-full items-center no-wrap gap-1"):
                ui.switch(value=entry["on"], on_change=lambda e, ev=event: self._whole(
                    f"on/{ev}", lambda d: d.set_list_event_on(self._layer, self._name, ev, e.value))) \
                    .props("dense").tooltip("Off: not shown in the list on stream; its look stays")
                ui.label(LIST_EVENTS[event]).classes("flex-1 min-w-0 truncate text-sm")
                ui.button("Look", icon="table_chart", on_click=lambda ev=event: self._look(ev)) \
                    .props("no-caps flat dense").tooltip("How it looks in the list: a table of cells")
                ui.button(icon="delete", on_click=lambda ev=event: self._whole(
                    "", lambda d: d.remove_list_event(self._layer, self._name, ev))) \
                    .props("flat round dense size=sm").tooltip("Take it out of the list (Undo brings it back)")
        left = {key: title for key, title in LIST_EVENTS.items()
                if key not in {entry["event"] for entry in now["entries"]}}
        if left:
            ui.select(left, label="Add an event", on_change=lambda e: e.value and self._whole(
                "", lambda d: d.add_list_event(self._layer, self._name, e.value))) \
                .props(FIELD).classes("w-full")

        ui.label("The list").classes("text-sm font-semibold pt-1")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.number("How many", value=now["count"], min=1, max=100, step=1,
                      on_change=lambda e: e.value and self._set("count", e.value)).props(FIELD) \
                .classes("flex-1 min-w-0").tooltip("The oldest goes when a new one comes and the list is full")
            ui.number("Space between", value=now["gap"], min=0, step=1, suffix="px",
                      on_change=lambda e: e.value is not None and self._set("gap", e.value)).props(FIELD) \
                .classes("flex-1 min-w-0")
        ui.select(NEWEST, value=now["newest"], label="New ones come in",
                  on_change=lambda e: e.value and self._set("newest", e.value)).props(FIELD).classes("w-full")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.select(LIST_ANIMATIONS, value=now["enter"], label="How they come in",
                      on_change=lambda e: self._set("enter", e.value or "")).props(FIELD).classes("flex-1 min-w-0")
            ui.number("Seconds", value=now["enter_seconds"], min=0, max=10, step=0.1,
                      on_change=lambda e: self._set("enter_seconds", e.value or 0)).props(FIELD).classes("w-24")
        with ui.row().classes("w-full no-wrap items-center gap-2"):
            goes = ui.switch("Goes away after", value=bool(now["stays"]),
                             on_change=lambda e: (seconds.set_visibility(e.value),
                                                  self._set("stays", (seconds.value or 30) if e.value else 0))) \
                .props("dense").tooltip("Off: an entry stays until the list is full")
            seconds = ui.number("Seconds", value=now["stays"] or 30, min=1, step=1,
                                on_change=lambda e: goes.value and e.value and self._set("stays", e.value)) \
                .props(FIELD).classes("w-24")
            seconds.set_visibility(bool(now["stays"]))
        ui.switch("Show the last ones again when OBS loads it", value=now["keep"],
                  on_change=lambda e: self._set("keep", e.value)).props("dense") \
            .tooltip("Off: the list starts empty each time OBS loads the widget")
        ui.label("The list's biggest size is the piece's width and height: what doesn't fit is cut off.") \
            .classes("text-xs opacity-60")

    def _set(self, key: str, value: Any) -> None:
        self._change(f"{self._layer}/{self._name}/list/{key}",
                     lambda d: d.set_event_list(self._layer, self._name, **{key: value}))

    def _whole(self, key: str, what: Callable[[ElementDesign], Any]) -> None:
        """A change after which the panel is drawn again (an event added, taken out, switched)."""
        self._change(key or f"{self._layer}/{self._name}/events", what, whole=True, group=False)

    async def _look(self, event: str) -> None:
        await EntryTableDialog(self._design, self._layer, self._name, event, self._change, self._windows,
                               self._take_file, self._media, self._pick_file, self._values(event)).open()
