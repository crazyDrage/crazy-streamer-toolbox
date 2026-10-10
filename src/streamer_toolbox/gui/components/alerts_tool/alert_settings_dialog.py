import json
import uuid
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from nicegui import Client, app, context, ui

from streamer_toolbox.core.alerts.alert_actions import PICTURE_TYPES
from streamer_toolbox.core.alerts.alert_look import ANIMATIONS_IN, ANIMATIONS_OUT, PLACES, TEXT_PLACES, AlertLook
from streamer_toolbox.core.alerts.alert_part import ALIGNS, PARTS, AlertPart
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_rule import ALERT_EVENTS, AlertRule, default_parts
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.alerts.alert_variation import AlertVariation
from streamer_toolbox.core.files.file_types import AUDIO_TYPES
from streamer_toolbox.gui.components.file_dialog import FileDialog

FIELD = "outlined dense options-dense"
ADVANCED_KEY = "alert_look_advanced"  # app.storage.general: whether the window shows the advanced options


class AlertSettingsDialog:
    """Everything about one alert in one window. On the left the alert as it will be on stream (a frame of the
    overlay page in edit mode: it stays; a piece of the words that is "on the picture" is dragged there to where
    it fits, and the picture itself drags the whole alert across the screen). On the right its settings: the
    text, picture, sound, how long, the pieces of its words (a list he adds to and takes from: text line, name,
    amount, their message; each can be put on the picture, so a picture that is a card gets its boxes filled),
    where it is and how it comes in and goes out. The Advanced switch adds each piece's own words, width, size, colour and side, the
    sizes, colours and font of the alert, the smallest amount and the bigger alerts from an amount. Play shows
    it once with its animation. Every change is saved at once and seen at once; on_change() after each."""

    def __init__(self, store: AlertStore, queue: AlertQueue, event: str,
                 on_change: Callable[[], None] = lambda: None) -> None:
        self._store = store
        self._queue = queue
        self._event = event
        self._on_change = on_change
        self._frame = f"look_{uuid.uuid4().hex[:8]}"
        self._client: Client | None = None  # the page the window is on, see _send

    @property
    def _rule(self) -> AlertRule:
        return self._store.get(self._event)

    def open(self) -> None:
        self._client = context.client
        with ui.dialog().props("persistent") as dialog, ui.card().classes("w-[88rem] max-w-full gap-3"):
            with ui.row().classes("items-center no-wrap w-full"):
                ui.label(f"{self._rule.title} alert").classes("text-lg font-semibold flex-1")
                ui.switch("Advanced", value=bool(app.storage.general.get(ADVANCED_KEY, False)),
                          on_change=lambda e: self._set_advanced(e.value)).props("dense")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")
            with ui.element("div").classes("flex flex-col lg:flex-row w-full gap-4"):
                with ui.column().classes("flex-1 min-w-0 gap-2"):
                    with ui.element("div").classes("w-full rounded overflow-hidden border border-gray-500/30") \
                            .style("aspect-ratio: 16 / 9; background: repeating-conic-gradient(#2a2a2a 0% 25%, "
                                   "#1c1c1c 0% 50%) 0 0 / 24px 24px"):
                        ui.element("iframe").props(f"id={self._frame} src=/overlay/alerts?edit=1") \
                            .style("width: 100%; height: 100%; border: 0; display: block; color-scheme: light")
                    with ui.row().classes("items-center gap-2"):
                        ui.button("Play", icon="play_arrow", on_click=lambda: self._send("play")) \
                            .props("no-caps unelevated").tooltip("Shows it once, with its animation and sound")
                        ui.button("Back to the start look", icon="restart_alt", on_click=self._reset) \
                            .props("no-caps flat").tooltip("Places, pieces, animations, sizes and colours as "
                                                           "they were at the start; text and files stay")
                    ui.label("Drag a piece that is on the picture to where it fits. Drag the picture to move the "
                             "whole alert on the screen, and the round handle on its corner to make it bigger or "
                             "smaller (the words on it grow and shrink with it). The name, amount and message here are examples.") \
                        .classes("text-xs opacity-60")
                with ui.column().classes("w-full lg:w-[30rem] shrink-0 gap-2 max-h-[72vh] overflow-y-auto pr-1"):
                    self._options()
            with ui.row().classes("w-full justify-end"):
                ui.button("Done", icon="check", on_click=dialog.close).props("no-caps unelevated")
        ui.on(f"{self._frame}_ready", lambda: self._send("hold"))
        ui.on(f"{self._frame}_text", lambda e: self._moved(e.args))
        ui.on(f"{self._frame}_spot", lambda e: self._placed(e.args))
        ui.on(f"{self._frame}_size", lambda e: self._sized(e.args))
        ui.run_javascript(f"""
            window.addEventListener("message", event => {{
                const frame = document.getElementById("{self._frame}");
                if (!frame || event.source !== frame.contentWindow || !event.data) return;
                if (event.data.type === "toolbox_alert_ready") emitEvent("{self._frame}_ready", {{}});
                if (event.data.type === "toolbox_alert_text")
                    emitEvent("{self._frame}_text", {{index: event.data.index, x: event.data.x, y: event.data.y}});
                if (event.data.type === "toolbox_alert_spot")
                    emitEvent("{self._frame}_spot", {{x: event.data.x, y: event.data.y}});
                if (event.data.type === "toolbox_alert_size")
                    emitEvent("{self._frame}_size", {{height: event.data.height, sizes: event.data.sizes}});
            }});""")
        dialog.open()
        ui.timer(1.0, lambda: self._send("hold"), once=True)  # if the frame was ready before we listened

    # ---- the settings ----

    @ui.refreshable_method
    def _options(self) -> None:
        rule, look = self._rule, self._rule.look
        advanced = bool(app.storage.general.get(ADVANCED_KEY, False))
        _section("What it says and shows")
        ui.input("Text", value=rule.text, on_change=lambda e: self._change_rule(text=e.value or "")) \
            .props(FIELD + " debounce=300").classes("w-full")
        ui.label("Filled in: {user}" + (", {amount}" if rule.has_amount else "")
                 + (", {message}" if rule.has_message else "") + (", {currency}" if self._event == "tip" else "")) \
            .classes("text-xs opacity-60 -mt-1")
        self._file("Picture, gif or video", rule.image, PICTURE_TYPES, lambda v: self._change_rule(image=v))
        self._file("Sound", rule.sound, AUDIO_TYPES, lambda v: self._change_rule(sound=v))
        with ui.row().classes("no-wrap gap-2 w-full"):
            ui.number("Seconds", value=rule.seconds, min=0.5, max=120, step=0.5,
                      on_change=lambda e: self._change_rule(seconds=_number(e.value, 5))).props(FIELD).classes("flex-1")
            ui.number("Volume (0 to 1)", value=rule.volume, min=0, max=1, step=0.1,
                      on_change=lambda e: self._change_rule(volume=_number(e.value, 0))).props(FIELD).classes("flex-1")

        _section("The pieces of its words")
        ui.label("Add the pieces you want and take away the others. A piece that is on the picture gets a "
                 "dashed box in the preview: drag it to where it fits. For a picture that is a card, take the "
                 "text line away and put name, amount and message in their boxes.").classes("text-xs opacity-60")
        for index, part in enumerate(rule.parts):
            self._piece(index, part, advanced, bool(rule.image))
        if not rule.parts:
            ui.label("No pieces: this alert shows no words.").classes("text-xs opacity-60")
        with ui.dropdown_button("Add a piece", icon="add", auto_close=True).props("no-caps outline dense"):
            for kind, (title, _) in PARTS.items():
                if (kind == "amount" and not rule.has_amount) or (kind == "message" and not rule.has_message):
                    continue
                ui.item(title, on_click=lambda k=kind: self._add_part(k))
        ui.select(TEXT_PLACES, value=look.text_place, label="Pieces that aren't on the picture are",
                  on_change=lambda e: self._change_look(text_place=e.value)).props(FIELD).classes("w-full")

        _section("Where it is and how it moves")
        ui.select(PLACES, value=look.place, label="Where on the screen",
                  on_change=lambda e: self._change_look(place=e.value)).props(FIELD).classes("w-full")
        with ui.row().classes("no-wrap gap-2 w-full"):
            ui.select(ANIMATIONS_IN, value=look.animation_in, label="How it comes in",
                      on_change=lambda e: self._change_look(play=True, animation_in=e.value)) \
                .props(FIELD).classes("flex-1")
            ui.select(ANIMATIONS_OUT, value=look.animation_out, label="How it goes out",
                      on_change=lambda e: self._change_look(animation_out=e.value)).props(FIELD).classes("flex-1")
        if not advanced:
            return

        _section("Sizes, colours, font")
        with ui.row().classes("no-wrap gap-2 w-full"):
            ui.number("Animation seconds", value=look.animation_seconds, min=0, max=3, step=0.1,
                      on_change=lambda e: self._change_look(animation_seconds=_number(e.value, 0.4))) \
                .props(FIELD).classes("flex-1")
            ui.number("Picture height %", value=look.picture_height, min=5, max=100, step=5,
                      on_change=lambda e: self._change_look(picture_height=_number(e.value, 45))) \
                .props(FIELD).classes("flex-1").tooltip("Percent of the screen's height. At 45 a picture keeps "
                                                        "its own size unless it's bigger; any other number makes "
                                                        "it exactly that high")
            ui.number("Text size", value=look.text_size, min=10, max=200, step=2,
                      on_change=lambda e: self._change_look(text_size=_number(e.value, 44))) \
                .props(FIELD).classes("flex-1").tooltip("Pixels, on a 1080 high canvas")
        with ui.row().classes("no-wrap gap-2 w-full"):
            ui.color_input("Text colour", value=look.text_color,
                           on_change=lambda e: self._change_look(text_color=e.value or "")) \
                .props(FIELD + " clearable").classes("flex-1")
            ui.color_input("Name colour", value=look.accent_color,
                           on_change=lambda e: self._change_look(accent_color=e.value or "")) \
                .props(FIELD + " clearable").classes("flex-1")
        ui.input("Font", value=look.font, placeholder="e.g. Comic Sans MS (one installed on this PC)",
                 on_change=lambda e: self._change_look(font=e.value or "")).props(FIELD + " debounce=400") \
            .classes("w-full")
        ui.label("Empty colours and font = the overlay's own (white, purple names).").classes("text-xs opacity-60")

        if rule.has_amount:
            _section("Amounts")
            ui.number("Only from (smallest amount that gets an alert)", value=rule.minimum, min=0, step=1,
                      on_change=lambda e: self._change_rule(minimum=int(_number(e.value, 0)))) \
                .props(FIELD).classes("w-full")
            self._variations()

    def _piece(self, index: int, part: AlertPart, advanced: bool, has_picture: bool) -> None:
        with ui.card().props("flat bordered").classes("w-full gap-1 p-2"):
            with ui.row().classes("items-center no-wrap gap-1 w-full"):
                ui.label(part.title).classes("text-sm font-semibold flex-1")
                ui.switch("On the picture", value=part.on_picture,
                          on_change=lambda e: self._put_on_picture(index, e.value)).props("dense").classes("mr-2")
                if index:
                    ui.button(icon="arrow_upward", on_click=lambda: self._part_up(index)) \
                        .props("flat round dense").tooltip("One place up in the list (and in the stack of words)")
                ui.button(icon="delete", on_click=lambda: self._drop_part(index)) \
                    .props("flat round dense").tooltip("Take this piece away")
            if part.on_picture and not has_picture:
                ui.label("This alert has no picture yet: give it one above, then this piece can sit on it.") \
                    .classes("text-xs text-warning")
            if not advanced:
                return
            ui.input("What it says", value=part.text,
                     placeholder=PARTS[part.kind][1] or "the alert's Text, above",
                     on_change=lambda e: self._change_part(index, text=e.value or "")) \
                .props(FIELD + " debounce=300").classes("w-full") \
                .tooltip("e.g. {amount} months. Empty = just the value (a text line: the alert's Text)")
            with ui.row().classes("no-wrap gap-2 w-full"):
                ui.number("Size", value=part.size or None, min=0, max=300, step=2, placeholder="as the alert",
                          on_change=lambda e: self._change_part(index, size=_number(e.value, 0))) \
                    .props(FIELD).classes("flex-1")
                ui.color_input("Colour", value=part.color,
                               on_change=lambda e: self._change_part(index, color=e.value or "")) \
                    .props(FIELD + " clearable").classes("flex-1")
            if part.on_picture:
                with ui.row().classes("no-wrap gap-2 w-full"):
                    ui.select(ALIGNS, value=part.align, label="It starts at its",
                              on_change=lambda e: self._change_part(index, align=e.value)) \
                        .props(FIELD).classes("flex-1") \
                        .tooltip("Left: the spot you drag it to is where its words begin (good for a box to fill)")
                    ui.number("Width %", value=part.width or None, min=0, max=100, step=5, placeholder="as needed",
                              on_change=lambda e: self._change_part(index, width=_number(e.value, 0))) \
                        .props(FIELD).classes("flex-1") \
                        .tooltip("How much of the picture's width it may use before its words wrap")

    @ui.refreshable_method
    def _variations(self) -> None:
        """Bigger alerts from an amount on: per row the amount and its own text / picture / sound (empty = as
        the alert)."""
        variations = self._rule.variations
        ui.label("Bigger alerts from an amount" + (f" ({len(variations)})" if variations else "")) \
            .classes("text-sm font-semibold pt-1")
        ui.label("E.g. from 1000 bits another picture and sound. What you leave empty stays as the alert has it; "
                 "the highest amount that is reached wins.").classes("text-xs opacity-60")
        for index, variation in enumerate(variations):
            with ui.card().props("flat bordered").classes("w-full gap-2 p-2"):
                with ui.row().classes("items-center no-wrap gap-2 w-full"):
                    ui.number("From", value=variation.minimum, min=0, step=1,
                              on_change=lambda e, i=index: self._vary(i, minimum=int(_number(e.value, 0)))) \
                        .props(FIELD).classes("w-28 shrink-0")
                    ui.input("Text (empty = as the alert)", value=variation.text,
                             on_change=lambda e, i=index: self._vary(i, text=e.value or "")) \
                        .props(FIELD).classes("flex-1 min-w-0")
                    ui.button(icon="play_arrow", on_click=lambda v=variation: self._send("play", v.minimum)) \
                        .props("flat round dense").tooltip("Play it with this amount")
                    ui.button(icon="delete", on_click=lambda i=index: self._drop_variation(i)) \
                        .props("flat round dense").tooltip("Take this one away")
                self._file("Picture (empty = as the alert)", variation.image, PICTURE_TYPES,
                           lambda value, i=index: self._vary(i, image=value))
                self._file("Sound (empty = as the alert)", variation.sound, AUDIO_TYPES,
                           lambda value, i=index: self._vary(i, sound=value))
        ui.button("Add one", icon="add", on_click=self._add_variation).props("no-caps outline dense")

    @staticmethod
    def _file(label: str, value: str, endings: tuple[str, ...], save: Callable[[str], None]) -> None:
        with ui.row().classes("items-center no-wrap gap-1 w-full"):
            box = ui.input(label, value=value, on_change=lambda e: save((e.value or "").strip())) \
                .props(FIELD + " clearable").classes("flex-1 min-w-0")

            async def pick() -> None:
                path = await FileDialog(endings).open(box.value or "")
                if path:
                    box.set_value(path)

            ui.button(icon="folder_open", on_click=pick).props("flat round dense").tooltip("Pick a file on this PC")

    # ---- changes ----

    def _set_advanced(self, on: bool) -> None:
        app.storage.general[ADVANCED_KEY] = on
        self._options.refresh()

    def _save(self, rule: AlertRule, redraw: bool = False, play: bool = False) -> None:
        self._store.save(rule)
        self._on_change()
        self._send("play" if play else "hold")
        if redraw:
            self._options.refresh()

    def _change_rule(self, **values: Any) -> None:
        self._save(replace(self._rule, **values), redraw="image" in values)

    def _change_look(self, play: bool = False, **values: Any) -> None:
        self._save(replace(self._rule, look=replace(self._rule.look, **values).checked()), play=play)

    def _change_part(self, index: int, redraw: bool = False, **values: Any) -> None:
        self._save(self._rule.with_part(index, replace(self._rule.parts[index], **values)), redraw=redraw)

    def _put_on_picture(self, index: int, on: bool) -> None:
        """On: a piece that was never dragged gets a spot of its own below the ones already on the picture, so
        the boxes don't start on top of each other."""
        part = self._rule.parts[index]
        if on and (part.x, part.y) == (50.0, 50.0):
            there = sum(1 for p in self._rule.parts if p.on_picture)
            self._change_part(index, redraw=True, on_picture=True, y=min(15.0 + 17.5 * there, 85.0))
        else:
            self._change_part(index, redraw=True, on_picture=on)

    def _add_part(self, kind: str) -> None:
        self._save(self._rule.add_part(AlertPart(kind)), redraw=True)

    def _drop_part(self, index: int) -> None:
        self._save(self._rule.without_part(index), redraw=True)

    def _part_up(self, index: int) -> None:
        self._save(self._rule.part_up(index), redraw=True)

    def _moved(self, spot: dict[str, Any]) -> None:
        """A piece was dragged in the preview: where its anchor is now, in percent of the picture."""
        index, rule = spot.get("index"), self._rule
        if isinstance(index, int) and 0 <= index < len(rule.parts):
            self._store.save(rule.with_part(index, replace(rule.parts[index], x=float(spot["x"]),
                                                           y=float(spot["y"]))))
            self._on_change()

    def _placed(self, spot: dict[str, Any]) -> None:
        """The whole alert was dragged in the preview: its middle, in percent of the screen."""
        look = replace(self._rule.look, place="free", screen_x=float(spot["x"]), screen_y=float(spot["y"]))
        self._store.save(replace(self._rule, look=look.checked()))
        self._on_change()
        self._options.refresh()

    def _sized(self, size: dict[str, Any]) -> None:
        """The picture's corner was dragged in the preview: its height, in percent of the screen, and the new
        sizes of the pieces that are on it (they grow and shrink with the picture), as [place in the list, size]."""
        rule = self._rule
        rule = replace(rule, look=replace(rule.look, picture_height=float(size["height"])).checked())
        for index, pixels in size.get("sizes") or []:
            if isinstance(index, int) and 0 <= index < len(rule.parts) and rule.parts[index].on_picture:
                rule = rule.with_part(index, replace(rule.parts[index], size=max(1.0, min(float(pixels), 300.0))))
        self._store.save(rule)
        self._on_change()
        self._send("hold")  # the frame draws it again from what was saved
        self._options.refresh()

    def _reset(self) -> None:
        self._save(replace(self._rule, look=AlertLook(), parts=default_parts(self._event)), redraw=True)

    def _add_variation(self) -> None:
        rule = self._rule
        highest = max((v.minimum for v in rule.variations), default=0)
        self._store.save(replace(rule, variations=(*rule.variations, AlertVariation(max(highest * 2, 100)))))
        self._on_change()
        self._variations.refresh()

    def _drop_variation(self, index: int) -> None:
        rule = self._rule
        self._store.save(replace(rule, variations=tuple(v for i, v in enumerate(rule.variations) if i != index)))
        self._on_change()
        self._variations.refresh()

    def _vary(self, index: int, **values: Any) -> None:
        rule = self._rule
        self._store.save(replace(rule, variations=tuple(replace(v, **values) if i == index else v
                                                        for i, v in enumerate(rule.variations))))
        self._on_change()

    def _send(self, kind: str, amount: int | None = None) -> None:
        """hold: the alert stands in the frame; play: once, with its animation, then the standing one is back.
        amount: as if that many came (a bigger alert's own picture and words). Goes through the page the
        window was opened on, not through ui.run_javascript: that asks the element that was clicked for its
        page, and after a redraw of the settings that element is gone (the preview then never got the change)."""
        rule = self._rule
        example = dict(ALERT_EVENTS[self._event][3])
        if amount is not None and rule.has_amount:
            example[ALERT_EVENTS[self._event][2]] = amount
        try:
            payload = self._queue.payload(rule.alert_for(example))
        except FileNotFoundError as e:
            with self._client:
                ui.notify(str(e), type="warning", multi_line=True)
            return
        message = json.dumps({"type": kind, "alert": payload})
        self._client.run_javascript(f'document.getElementById("{self._frame}")?.contentWindow.postMessage({message}, "*")')


def _section(title: str) -> None:
    ui.label(title).classes("text-xs font-semibold uppercase tracking-wider text-primary pt-2")


def _number(value: Any, fallback: float) -> float:
    return float(value) if isinstance(value, (int, float)) else fallback
