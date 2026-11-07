from collections.abc import Awaitable, Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.widgets.element_design import AMOUNTS, ElementDesign
from streamer_toolbox.gui.components.widgets_tool.design_piece_panel import EVENT_NAMES, FIELD

# what a layer can be: always there, or an alert for an event
WHATS = {"": "Always there", **{event: f"{name} alert" for event, name in EVENT_NAMES.items()}}

# do(key, what): `what` changes the design and gives the layer to edit next (None: the same); the key groups a
# run of changes into one undo step
Do = Callable[[str, Callable[[ElementDesign], int | None]], None]


class DesignLayerPanel:
    """The layers of a widget in the widget editor (WidgetDesigner), as he asked (2026-11-06): add, rename,
    change, copy, reorder, switch off and delete them. The list shows the one in front on top, as the pieces
    list does; for alerts of one event the top one that fits plays. Under it the settings of the layer being
    edited: its name, what it is (always there or an alert), in front of the alerts or behind, and an alert's
    own condition (only from 100 bits, only some of the time)."""

    def __init__(self, design: ElementDesign, layer: int, windows: ui.element, pick: Callable[[int], None],
                 do: Do, remove: Callable[[int], Awaitable[None]]) -> None:
        self._design = design
        self._layer = layer
        self._windows = windows
        self._pick = pick
        self._do = do
        self._remove = remove

    def build(self) -> None:
        with ui.row().classes("w-full items-center no-wrap gap-1"):
            ui.label("Layers, the front one on top").classes("text-sm font-semibold flex-1")
            ui.button("Layer", icon="add", on_click=self._add).props("no-caps outline dense size=sm") \
                .tooltip("A new layer: always there, or an alert for an event")
        for number, title in reversed(self._design.layers()):
            self._row(number, title)
        self._settings()

    def _row(self, number: int, title: str) -> None:
        picked = number == self._layer
        on = self._design.is_on(number)
        alert = bool(self._design.event_of(number))
        with ui.row().classes("w-full items-center no-wrap gap-1 rounded px-1 cursor-pointer "
                              + ("bg-primary/20" if picked else "hover:bg-gray-500/10")) \
                .on("click", lambda n=number: self._pick(n)):
            ui.icon("notifications_active" if alert else "layers", size="xs").classes("opacity-70")
            with ui.column().classes("flex-1 min-w-0 gap-0"):
                ui.label(title).classes("text-sm truncate w-full" + ("" if on else " line-through opacity-50"))
                caption = self._caption(number)
                if caption:
                    ui.label(caption).classes("text-xs opacity-60 truncate w-full")
            if picked:
                count = len(self._design.layers())
                for icon, tip, step in (("arrow_upward", "Further in front", 1),
                                        ("arrow_downward", "Further back", -1)):
                    ui.button(icon=icon, on_click=lambda s=step, n=number: self._do(
                        "", lambda d: d.move_layer(n, s))) \
                        .props("flat round dense size=sm").tooltip(tip) \
                        .set_enabled(0 <= number + step < count)
                ui.button(icon="content_copy", on_click=lambda n=number: self._do(
                    "", lambda d: d.duplicate_layer(n))) \
                    .props("flat round dense size=sm").tooltip("Copy it with its pieces (a variation of an alert)")
                ui.button(icon="delete", on_click=lambda n=number: self._remove(n)) \
                    .props("flat round dense size=sm").tooltip("Delete it and its pieces")
            ui.button(icon="visibility" if on else "visibility_off",
                      on_click=lambda n=number, o=on: self._do("", lambda d: d.set_on(n, not o))) \
                .props("flat round dense size=sm").classes("" if on else "opacity-50") \
                .tooltip("On stream" if on else "Off: not shown on stream (stays here)")

    def _caption(self, number: int) -> str:
        event = self._design.event_of(number)
        if not event:
            return "Always there, in front of the alerts" if self._design.in_front(number) else ""
        condition = self._design.condition(number)
        words = []
        unit = AMOUNTS.get(event, "")
        if condition["at_least"] is not None and condition["at_most"] is not None:
            words.append(f"{_plain(condition['at_least'])} to {_plain(condition['at_most'])} {unit}")
        elif condition["at_least"] is not None:
            words.append(f"{_plain(condition['at_least'])} {unit} or more")
        elif condition["at_most"] is not None:
            words.append(f"up to {_plain(condition['at_most'])} {unit}")
        if condition["chance"] is not None:
            words.append(f"{_plain(condition['chance'])}% of the time")
        if condition["other"]:
            words.append("a condition from StreamElements")
        return " · ".join(words)

    def _settings(self) -> None:
        number = self._layer
        event = self._design.event_of(number)
        ui.separator().classes("my-1")
        ui.label("This layer").classes("text-xs uppercase opacity-60")
        ui.input("Name", value=self._design.layer_name(number)).props(FIELD).classes("w-full") \
            .on("blur", lambda e: self._rename(e.sender.value)) \
            .on("keydown.enter", lambda e: self._rename(e.sender.value))
        whats = WHATS if event in WHATS else {**WHATS, event: f"{event} alert"}
        ui.select(whats, value=event, label="It is",
                  on_change=lambda e: e.value is not None and e.value != event and self._do(
                      "", lambda d: d.set_layer_event(number, e.value))) \
            .props(FIELD).classes("w-full") \
            .tooltip("Always there: what the widget shows all the time. An alert: shown when that event comes, "
                     "one after the other")
        if not event:
            ui.switch("In front of the alerts", value=self._design.in_front(number),
                      on_change=lambda e: self._do("", lambda d: d.set_in_front(number, e.value))).props("dense") \
                .tooltip("Off: the alerts show over it")
            return
        self._condition(number, event)

    def _condition(self, number: int, event: str) -> None:
        now = self._design.condition(number)

        def set_(key: str, value: Any) -> None:
            self._do(f"cond/{number}/{key}", lambda d: d.set_condition(number, **{key: value}))
        ui.label("Plays only when").classes("text-sm font-semibold pt-1")
        if event in AMOUNTS:
            unit = AMOUNTS[event]
            with ui.row().classes("w-full no-wrap gap-2"):
                ui.number(f"At least ({unit})", value=now["at_least"], min=0,
                          on_change=lambda e: set_("at_least", e.value)).props(FIELD + " clearable") \
                    .classes("flex-1 min-w-0")
                ui.number(f"At most ({unit})", value=now["at_most"], min=0,
                          on_change=lambda e: set_("at_most", e.value)).props(FIELD + " clearable") \
                    .classes("flex-1 min-w-0")
        ui.number("Chance (%)", value=now["chance"], min=0, max=100, step=5,
                  on_change=lambda e: set_("chance", e.value)).props(FIELD + " clearable").classes("w-full") \
            .tooltip("Plays only this often: two follow alerts with 50% take turns by chance")
        if now["other"]:
            ui.label("It also has a condition from StreamElements that this editor keeps as it is.") \
                .classes("text-xs opacity-60")
        ui.label("Empty: always. When several alerts for one event fit, the top one in the list plays; one "
                 "without a condition plays when no other fits.").classes("text-xs opacity-60")

    def _rename(self, new: str) -> None:
        if new.strip() and new.strip() != self._design.layer_name(self._layer):
            number = self._layer
            self._do("", lambda d: d.rename_layer(number, new) and None)

    async def _add(self) -> None:
        with self._windows, ui.dialog() as dialog, ui.card().classes("w-96 gap-3"):
            ui.label("A new layer").classes("text-lg font-semibold")
            what = ui.select(WHATS, value="", label="It is").props(FIELD).classes("w-full")
            name = ui.input("Name (empty: from what it is)").props(FIELD).classes("w-full") \
                .on("keydown.enter", lambda: dialog.submit(True))
            ui.label("A second alert for an event is a variation: it gets a condition (from 100 bits on, or "
                     "by chance) that you can change.").classes("text-xs opacity-60")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Add", on_click=lambda: dialog.submit(True)).props("unelevated no-caps")
        sure = await dialog
        dialog.delete()
        if sure:
            event, wanted = what.value or "", name.value or ""
            self._do("", lambda d: d.add_layer(event, wanted))


def _plain(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)
