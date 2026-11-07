from collections.abc import Awaitable, Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.widgets.design_values import DesignValues
from streamer_toolbox.core.widgets.element_design import (ANIMATIONS_IN, ANIMATIONS_OUT, KINDS, REACTIONS,
                                                          ElementDesign)
from streamer_toolbox.core.widgets.element_settings import _number
from streamer_toolbox.gui.components.widgets_tool.design_live_panel import DesignLivePanel

FIELD = "outlined dense options-dense"
FONTS = ["Arial", "Arial Black", "Verdana", "Tahoma", "Trebuchet MS", "Segoe UI", "Georgia", "Times New Roman",
         "Courier New", "Impact", "Comic Sans MS", "Consolas"]
SHADOW = "2px 2px 4px #000000"
OUTLINE = "3px #000000"
# where the align buttons put a piece on the canvas (widget_designer.js align)
ALIGN = (("align_horizontal_left", "To the left edge", "left"),
         ("align_horizontal_center", "In the middle, across", "center"),
         ("align_horizontal_right", "To the right edge", "right"),
         ("align_vertical_top", "To the top", "top"), ("align_vertical_center", "In the middle, up and down", "middle"),
         ("align_vertical_bottom", "To the bottom", "bottom"))
# an alert layer's event → its name in the editor
EVENT_NAMES = {"follower": "Follow", "subscriber": "Sub", "communityGiftPurchase": "Gifted subs",
               "cheer": "Cheer", "raid": "Raid", "tip": "Tip"}

# change(key, what): `what` changes the design; the key groups a run of changes into one undo step (typing)
Change = Callable[[str, Callable[[ElementDesign], Any]], None]


class DesignPiecePanel:
    """The settings of the piece picked in the widget editor (WidgetDesigner): its text and the values in it,
    its file, look, place and how it moves; a shape's colours, a goal bar's and a ticker's settings
    (DesignLivePanel). Each change goes through `change`, which redraws the canvas and saves; the panel itself
    is drawn again only when another piece is picked."""

    def __init__(self, design: ElementDesign, layer: int, name: str, change: Change,
                 pick_file: Callable[[], Awaitable[None]], upload: Callable[[Any], Awaitable[None]],
                 try_reaction: Callable[[list[str]], None], align: Callable[[str], None]) -> None:
        self._design = design
        self._layer = layer
        self._name = name
        self._change = change
        self._pick_file = pick_file
        self._upload = upload
        self._try = try_reaction
        self._align = align

    def build(self) -> None:
        piece = self._design.piece(self._layer, self._name)
        kind = piece.get("type")
        alert = bool(self._design.event_of(self._layer))
        ui.label(KINDS.get(kind, str(kind))).classes("text-xs uppercase opacity-60")
        ui.input("Name", value=self._name).props(FIELD).classes("w-full") \
            .on("blur", lambda e: self._rename(e.sender.value)) \
            .on("keydown.enter", lambda e: self._rename(e.sender.value))
        live = DesignLivePanel(self._design, self._layer, self._name, self._set)
        if kind == "text" or (kind == "latestTicker" and self._design.ticker(self._layer, self._name) is None):
            self._words(alert)
        if kind == "latestTicker":
            live.ticker()
        if kind == "goal":
            live.goal()
        if kind in ("text", "latestTicker", "goal"):
            self._look(kind)
        if kind == "shape":
            self._shape()
        if kind in ("image", "video", "audio"):
            self._file(kind)
        if kind in ("video", "audio"):
            ui.label("Volume").classes("text-xs opacity-70")
            ui.slider(min=0, max=100, step=5, value=round(float(piece.get("volume", 1)) * 100),
                      on_change=lambda e: self._set("volume", lambda d: d.set_volume(self._layer, self._name,
                                                                                    e.value / 100))) \
                .props("label")
        if kind == "audio" and alert:
            ui.number("Starts after (seconds)", value=float(piece.get("delaySeconds") or 0), min=0, step=0.1,
                      on_change=lambda e: self._set("delay", lambda d: d.set_delay(self._layer, self._name,
                                                                                  e.value or 0))) \
                .props(FIELD).classes("w-full")
        if kind != "audio":
            self._place(kind)
        if alert and kind != "audio":
            self._animation()
        elif not alert:
            self._reaction()

    def _set(self, key: str, what: Callable[[ElementDesign], Any]) -> None:
        self._change(f"{self._layer}/{self._name}/{key}", what)

    def _style(self, key: str, **style: Any) -> None:
        self._set(key, lambda d: d.set_style(self._layer, self._name, **style))

    def _rename(self, new: str) -> None:
        if new.strip() and new.strip() != self._name:
            self._change("rename", lambda d: d.rename(self._layer, self._name, new))

    def _words(self, alert: bool) -> None:
        box = ui.textarea("Text", value=DesignValues.to_words(self._design.text(self._layer, self._name)),
                          on_change=lambda e: self._set("text", lambda d: d.set_text(
                              self._layer, self._name, DesignValues.to_codes(e.value or "")))) \
            .props(FIELD + " autogrow").classes("w-full")
        names = [name for name, _ in DesignValues.names(alert)]

        def add_value(e) -> None:
            if e.value:
                box.set_value((box.value or "").rstrip(" ") + f" [{e.value}]")
                e.sender.set_value(None)
        ui.select(names, label="Add a value to the text", on_change=add_value).props(FIELD).classes("w-full") \
            .tooltip("A value shows as [its name] in the text and is filled in on stream"
                     + ("; in an alert the event's own values too (their name, the amount)" if alert else ""))

    def _look(self, kind: str) -> None:
        piece = self._design.piece(self._layer, self._name)
        style, highlight = piece.get("style") or {}, piece.get("highlightedStyle") or {}
        if kind != "text":
            ui.label("The words").classes("text-sm font-semibold pt-1")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.select(sorted({*FONTS, str(style.get("fontFamily") or "Arial")}), label="Font",
                      value=str(style.get("fontFamily") or "Arial"), new_value_mode="add-unique",
                      on_change=lambda e: self._style("font", fontFamily=e.value)) \
                .props(FIELD + " use-input").classes("flex-1 min-w-0") \
                .tooltip("A font on this PC; type another font's name to use it")
            ui.number("Size", value=_number(style.get("fontSize")) or 16, min=1, step=1,
                      on_change=lambda e: e.value and self._style("size", fontSize=f"{e.value}px")) \
                .props(FIELD).classes("w-24")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.color_input("Colour", value=str(style.get("color") or "#ffffff"),
                           on_change=lambda e: e.value and self._style("color", color=e.value)) \
                .props(FIELD).classes("flex-1 min-w-0")
            if kind != "goal":
                ui.color_input("Names' colour" if kind == "latestTicker" else "Values' colour",
                               value=str(highlight.get("color") or style.get("color") or "#ffffff"),
                               on_change=lambda e: e.value and self._set("highlight", lambda d: d.set_highlight(
                                   self._layer, self._name, e.value))) \
                    .props(FIELD).classes("flex-1 min-w-0").tooltip("The colour of the filled-in values")
        with ui.row().classes("w-full items-center gap-x-3 gap-y-1"):
            if kind != "goal":  # a goal bar's words are in its middle
                ui.toggle({"left": "Left", "center": "Middle", "right": "Right"},
                          value=str(style.get("textAlign") or "left"),
                          on_change=lambda e: self._style("align", textAlign=e.value)).props("dense no-caps")
            ui.switch("Bold", value=str(style.get("fontWeight") or "") in ("bold", "700", "800", "900"),
                      on_change=lambda e: self._style("bold", fontWeight="bold" if e.value else "normal")) \
                .props("dense")
            ui.switch("Shadow", value=bool(style.get("textShadow")),
                      on_change=lambda e: self._style("shadow", textShadow=SHADOW if e.value else None)) \
                .props("dense")
            ui.switch("Outline", value=bool(style.get("webkitTextStroke")),
                      on_change=lambda e: self._style("outline", webkitTextStroke=OUTLINE if e.value else None,
                                                      paintOrder="stroke fill" if e.value else None)) \
                .props("dense")

    def _file(self, kind: str) -> None:
        file = self._design.file(self._layer, self._name)
        ui.label(file or "No file yet").classes("font-mono text-xs break-all" + ("" if file else " opacity-60"))
        with ui.row().classes("w-full items-center gap-2"):
            ui.button("Pick a file on the PC", icon="folder_open", on_click=self._pick_file) \
                .props("no-caps outline dense")
        accept = {"image": "image/*", "video": "video/webm,video/mp4", "audio": "audio/*"}[kind]
        ui.upload(on_upload=self._upload, auto_upload=True, max_files=1) \
            .props(f'accept="{accept}" flat bordered dense label="Or from this device: + or drop it here"') \
            .classes("w-full")
        if kind == "image":
            ui.label("A GIF moves on stream as it does here. A video with see-through parts: WebM.") \
                .classes("text-xs opacity-60")

    def _shape(self) -> None:
        style = self._design.piece(self._layer, self._name).get("style") or {}
        border = str(style.get("border") or "").split()
        ui.label("The shape").classes("text-sm font-semibold pt-1")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.color_input("Colour", value=str(style.get("backgroundColor") or ""),
                           on_change=lambda e: self._style("fill", backgroundColor=e.value or None)) \
                .props(FIELD).classes("flex-1 min-w-0")
            round_ = str(style.get("borderRadius", "")).endswith("%")  # a circle (the add list's): no pixels
            ui.number("Corners", value=None if round_ else _number(style.get("borderRadius")) or 0, min=0, step=2,
                      placeholder="round" if round_ else "",
                      on_change=lambda e: self._style("corners", borderRadius=f"{e.value}px" if e.value else None)) \
                .props(FIELD).classes("w-24").tooltip("How round the corners are (pixels)")
        with ui.row().classes("w-full no-wrap gap-2"):
            line = {"width": _number(border[0]) if border else 0, "color": border[2] if len(border) > 2 else "#ffffff"}

            def set_border(**changes: Any) -> None:
                line.update(changes)
                self._style("border", border=f"{line['width']}px solid {line['color']}" if line["width"] else None)
            ui.number("Border", value=line["width"], min=0, step=1,
                      on_change=lambda e: set_border(width=e.value or 0)).props(FIELD).classes("w-24")
            ui.color_input("Border colour", value=line["color"],
                           on_change=lambda e: e.value and set_border(color=e.value)) \
                .props(FIELD).classes("flex-1 min-w-0")
        ui.switch("Soft shadow", value=bool(style.get("boxShadow")),
                  on_change=lambda e: self._style("glow", boxShadow="0 6px 24px rgba(0, 0, 0, 0.5)" if e.value
                                                  else None)).props("dense")

    def _place(self, kind: str) -> None:
        style = (self._design.piece(self._layer, self._name).get("style") or {})
        ui.label("Place and look").classes("text-sm font-semibold pt-1")
        with ui.row().classes("w-full no-wrap gap-0 justify-between"):
            for icon, tip, how in ALIGN:
                ui.button(icon=icon, on_click=lambda h=how: self._align(h)).props("flat round dense size=sm") \
                    .tooltip(tip)
        sides = (("left", "X"), ("top", "Y"), ("width", "Width")) + ((("height", "Height"),)
                                                                    if kind in ("shape", "goal") else ())
        with ui.row().classes("w-full no-wrap gap-2"):
            for side, label in sides:
                ui.number(label, value=_number(style.get(side)), step=1,
                          on_change=lambda e, s=side: e.value is not None and self._style(s, **{s: f"{e.value}px"})) \
                    .props(FIELD).classes("flex-1 min-w-0")
        with ui.row().classes("w-full no-wrap items-center gap-2"):
            ui.label("See-through").classes("text-xs opacity-70 shrink-0")
            opacity = _number(style.get("opacity"))
            ui.slider(min=0, max=100, step=5, value=100 - round((1 if opacity is None else opacity) * 100),
                      on_change=lambda e: self._style("opacity", opacity=None if not e.value
                                                      else str(round(1 - e.value / 100, 2)))) \
                .props("label").classes("flex-1")
            ui.number("Turn (°)", value=_degrees(style.get("rotate")), step=1,
                      on_change=lambda e: self._style("rotate", rotate=f"{e.value}deg" if e.value else None)) \
                .props(FIELD).classes("w-24")

    def _animation(self) -> None:
        now = self._design.animation(self._layer, self._name)

        def set_(key: str, value: Any) -> None:
            self._set(f"anim/{key}", lambda d: d.set_animation(self._layer, self._name, **{key: value}))
        ui.label("When the alert plays").classes("text-sm font-semibold pt-1")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.select(ANIMATIONS_IN, value=now["in"], label="Comes in",
                      on_change=lambda e: set_("in", e.value)).props(FIELD).classes("flex-1 min-w-0")
            ui.number("Seconds", value=now["in_seconds"], min=0, max=10, step=0.1,
                      on_change=lambda e: set_("in_seconds", e.value or 0)).props(FIELD).classes("w-24")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.number("After (s)", value=now["delay"], min=0, step=0.1,
                      on_change=lambda e: set_("delay", e.value or 0)).props(FIELD).classes("flex-1 min-w-0") \
                .tooltip("It comes in this long after the alert starts")
            ui.number("Stays (s)", value=now["stays"], min=0, step=0.5,
                      on_change=lambda e: set_("stays", e.value or 0)).props(FIELD).classes("flex-1 min-w-0") \
                .tooltip("0 for a video: as long as the video runs")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.select(ANIMATIONS_OUT, value=now["out"], label="Goes out",
                      on_change=lambda e: set_("out", e.value)).props(FIELD).classes("flex-1 min-w-0")
            ui.number("Seconds", value=now["out_seconds"], min=0, max=10, step=0.1,
                      on_change=lambda e: set_("out_seconds", e.value or 0)).props(FIELD).classes("w-24")

    def _reaction(self) -> None:
        now = self._design.reaction(self._layer, self._name)
        state = dict(now)

        def set_(**changes: Any) -> None:
            state.update(changes)
            self._set("react", lambda d: d.set_reaction(self._layer, self._name, state["events"],
                                                        state["animation"], state["seconds"]))
        ui.label("When an event comes").classes("text-sm font-semibold pt-1")
        ui.select(EVENT_NAMES, value=now["events"], multiple=True, label="On",
                  on_change=lambda e: set_(events=list(e.value or []))).props(FIELD + " use-chips") \
            .classes("w-full").tooltip("E.g. the latest follower's name pops when someone follows")
        with ui.row().classes("w-full no-wrap items-center gap-2"):
            ui.select(REACTIONS, value=now["animation"], label="It does",
                      on_change=lambda e: set_(animation=e.value)).props(FIELD).classes("flex-1 min-w-0")
            ui.number("Seconds", value=now["seconds"], min=0.1, max=10, step=0.1,
                      on_change=lambda e: set_(seconds=e.value or 0.8)).props(FIELD).classes("w-24")
            ui.button(icon="play_arrow", on_click=lambda: self._try(state["events"])) \
                .props("flat round dense").tooltip("Try it: a test event in the preview")


def _degrees(text: Any) -> float:
    """"15deg" → 15; 0 for nothing or anything else."""
    try:
        return float(str(text or "0").strip().removesuffix("deg"))
    except ValueError:
        return 0
