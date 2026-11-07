from collections.abc import Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.widgets.element_design import GOALS, TICKER_LOOKS, TICKERS, ElementDesign

FIELD = "outlined dense options-dense"

# set(key, what): `what` changes the design; the key groups a run of changes into one undo step (typing)
Set = Callable[[str, Callable[[ElementDesign], Any]], None]


class DesignLivePanel:
    """The settings of the widget editor's pieces that follow the stream by themselves: a goal bar (what it
    counts, up to where, its words, its colours) and a ticker of the recent ones (whose names, how many, how
    it shows them). Part of DesignPiecePanel; the look of the words (font, size, colour) is the panel's."""

    def __init__(self, design: ElementDesign, layer: int, name: str, set_: Set) -> None:
        self._design = design
        self._layer = layer
        self._name = name
        self._set = set_

    def goal(self) -> None:
        now = self._design.goal(self._layer, self._name)
        piece = self._design.piece(self._layer, self._name)

        def set_(key: str, value: Any) -> None:
            self._set(f"goal/{key}", lambda d: d.set_goal(self._layer, self._name, **{key: value}))
        ui.label("The goal").classes("text-sm font-semibold pt-1")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.select(GOALS, value=now["value"], label="Counts",
                      on_change=lambda e: e.value and set_("value", e.value)).props(FIELD).classes("flex-1 min-w-0")
            ui.number("Goal", value=now["target"], min=1, step=1,
                      on_change=lambda e: e.value and set_("target", e.value)).props(FIELD).classes("w-28")
        ui.input("Words on it", value=now["label"],
                 on_change=lambda e: set_("label", e.value or "")).props(FIELD).classes("w-full") \
            .tooltip("{value} is the count, {target} the goal, {percent} how far it is")
        ui.label("{value} = the count, {target} = the goal, {percent} = how far. A new stream starts the "
                 "\"this stream\" ones at 0.").classes("text-xs opacity-60")
        style, fill = piece.get("style") or {}, piece.get("fillStyle") or {}
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.color_input("Reached", value=str(fill.get("backgroundColor") or "#9146ff"),
                           on_change=lambda e: e.value and self._set("fill", lambda d: d.set_fill(
                               self._layer, self._name, e.value))) \
                .props(FIELD).classes("flex-1 min-w-0")
            ui.color_input("To go", value=str(style.get("backgroundColor") or ""),
                           on_change=lambda e: self._set("back", lambda d: d.set_style(
                               self._layer, self._name, backgroundColor=e.value or None))) \
                .props(FIELD).classes("flex-1 min-w-0")

    def ticker(self) -> None:
        now = self._design.ticker(self._layer, self._name)
        if now is None:
            ui.label("A ticker from StreamElements: its text says whose names it shows.") \
                .classes("text-xs opacity-60")
            return

        def set_(key: str, value: Any) -> None:
            self._set(f"ticker/{key}", lambda d: d.set_ticker(self._layer, self._name, **{key: value}))
        ui.label("Whose names").classes("text-sm font-semibold pt-1")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.select(TICKERS, value=now["kind"], label="The recent",
                      on_change=lambda e: e.value and set_("kind", e.value)).props(FIELD).classes("flex-1 min-w-0")
            ui.number("How many", value=now["count"], min=1, max=25, step=1,
                      on_change=lambda e: e.value and set_("count", e.value)).props(FIELD).classes("w-28")
        with ui.row().classes("w-full no-wrap items-center gap-2"):
            ui.select(TICKER_LOOKS, value=now["look"], label="Shows them",
                      on_change=lambda e: e.value and set_("look", e.value)).props(FIELD).classes("flex-1 min-w-0")
            ui.switch("Amount", value=now["amount"], on_change=lambda e: set_("amount", e.value)).props("dense") \
                .tooltip("Bits, months, viewers or the tip after the name")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.input("Between them", value=now["between"],
                     on_change=lambda e: set_("between", e.value or "")).props(FIELD).classes("flex-1 min-w-0")
            ui.number("One round (s)", value=now["seconds"], min=1, step=1,
                      on_change=lambda e: e.value and set_("seconds", e.value)).props(FIELD).classes("w-28") \
                .tooltip("When it runs along: how long the names take to go by once")
