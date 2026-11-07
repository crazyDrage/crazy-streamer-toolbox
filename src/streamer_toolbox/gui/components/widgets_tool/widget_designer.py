import json
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from nicegui import ui

from streamer_toolbox.core.event_types.event_users import EventUsers
from streamer_toolbox.core.widgets.design_files import DesignFiles
from streamer_toolbox.core.widgets.design_preset import DesignPreset
from streamer_toolbox.core.widgets.design_values import DesignValues
from streamer_toolbox.core.widgets.element_design import ENDINGS, ElementDesign
from streamer_toolbox.core.widgets.widget import Widget
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore
from streamer_toolbox.gui.components.file_dialog import FileDialog
from streamer_toolbox.gui.components.widgets_tool.design_add_list import DesignAddList
from streamer_toolbox.gui.components.widgets_tool.design_layer_panel import DesignLayerPanel
from streamer_toolbox.gui.components.widgets_tool.design_piece_panel import EVENT_NAMES, FIELD, DesignPiecePanel

HEAD = '<link rel="stylesheet" href="/static/widget_designer.css"><script src="/static/widget_designer.js"></script>'
ICONS = {"text": "title", "image": "image", "video": "movie", "audio": "volume_up", "latestTicker": "view_carousel",
         "shape": "crop_square", "goal": "flag"}
# what the canvas draws a piece as (widget_designer.js)
DRAWN = {"text": "text", "latestTicker": "text", "image": "image", "video": "video", "shape": "shape",
         "goal": "goal"}
# what pulling a piece's corner does: a text gets bigger as a whole, a shape or a goal bar wider and higher on
# their own, the others only wider (a picture's height follows)
RESIZE = {"text": "scale", "shape": "free", "goal": "free"}
SIZES = {"1920x1080": "1920 × 1080 (full screen)", "1280x720": "1280 × 720", "1920x200": "1920 × 200 (a bar)",
         "800x600": "800 × 600", "1080x1920": "1080 × 1920 (standing)"}
# an alert layer's event → the test button's event (Overlay → Widgets' test events)
TEST_LISTENERS = {"follower": "follower-latest", "subscriber": "subscriber-latest", "cheer": "cheer-latest",
                  "raid": "raid-latest", "tip": "tip-latest", "communityGiftPurchase": "subscriber-latest"}
# an Element's event → the toolbox's event types it comes from (a widget only gets the types it is given)
EVENT_TYPES = {"follower": ("follow",), "subscriber": ("sub", "resub", "gift"),
               "communityGiftPurchase": ("community_gift",), "cheer": ("cheer",), "raid": ("raid",),
               "tip": ("tip",)}
UNDO_STEPS = 100
SAVE_AFTER = 0.6  # seconds without a change: then it is saved (and OBS loads it again)


def address(name: str) -> str:
    return f"/overlays?show=designer&widget={name}"


def _fitted(width: int, height: int) -> str:
    """The canvas (and the preview) as big as the window lets it be: the whole width, but no higher than the
    window under the editor's top rows (his round 85: "it should use the whole window"; widget_designer.js
    FITS_UNDER does the same)."""
    return f"aspect-ratio: {width} / {height}; width: min(100%, calc((100vh - 230px) * {width} / {height}))"


class WidgetDesigner:
    """The widget editor (his task of 2026-11-06): a widget made of pieces on a canvas, no code. Pictures and
    GIFs, videos, texts with values that fill in (latest follower, ...), sounds, shapes, goal bars and tickers
    of the recent ones; layers of his own (DesignLayerPanel), always there or an alert for an event (follow,
    sub, ...) whose pieces come in, stay and go out with the alert editor's animations, several for an event
    as variations (from 100 bits on); a piece that is always there can move when an event comes (pop on a
    follow).

    The canvas (widget_designer.js) shows the widget as on stream, shrunk: click a piece to pick it, drag it,
    pull its corner, arrow keys, Delete, Ctrl+Z / Ctrl+Y. On the right the layer's pieces and the picked one's
    settings (DesignPiecePanel). Preview is the real widget page with the test events. Every change is saved by
    itself (ElementDesign in the widget's JS part, as an imported StreamElements Element is kept: those open
    here too) and every page of the widget loads again, OBS too."""

    def __init__(self, store: WidgetStore, hub: WidgetHub, users: EventUsers, widget: Widget,
                 design: ElementDesign) -> None:
        self._store = store
        self._users = users
        self._hub = hub
        self._files = DesignFiles(store)
        self._name = widget.name
        self._design = design
        self._layer = design.layers()[0][0]
        self._picked = ""
        self._undo: list[tuple[ElementDesign, int, str]] = []
        self._redo: list[tuple[ElementDesign, int, str]] = []
        self._last_key = ""
        self._dirty = False
        self._quiet = 0.0
        self._stage = f"stage_{uuid.uuid4().hex[:8]}"
        self._event = f"design_{uuid.uuid4().hex[:8]}"
        self._windows: ui.element | None = None

    def build(self) -> None:
        ui.add_head_html(HEAD)
        self._windows = ui.element("div")
        with ui.row().classes("items-center w-full gap-2"):
            ui.label(f"Widget editor: {self._name}").classes("text-lg font-semibold")
            self._undo_buttons()
            ui.space()
            self._mode = ui.toggle({"edit": "Edit", "preview": "Preview"}, value="edit",
                                   on_change=lambda e: self._show_mode(e.value)).props("dense no-caps")
            ui.button("Size", icon="aspect_ratio", on_click=self._canvas_size).props("no-caps flat dense") \
                .tooltip("The widget's size: OBS's Browser source gets the same")
            ui.button("Widget page", icon="tune").props(f"no-caps flat dense href=/overlays?show=widgets&widget="
                                                        f"{self._name}") \
                .tooltip("Its OBS address, its events and its code (the settings this editor writes)")
        # his round 85: the whole window; what can be added in a list on the left, the canvas as big as the window
        # lets it be, layers and pieces on the right (both sides scroll on their own)
        with ui.element("div").classes("w-full flex flex-col lg:flex-row gap-3 items-start"):
            with ui.card().classes("tb-design-side order-2 lg:order-1 w-full lg:w-48 shrink-0 gap-0 p-2"):
                self._add_list()
            with ui.column().classes("order-1 lg:order-2 w-full lg:flex-1 min-w-0 gap-2"):  # on a phone: first
                self._layer_bar()
                self._edit_box = ui.column().classes("w-full gap-1 items-center")
                with self._edit_box:
                    ui.element("div").props(f"id={self._stage}").classes("tb-design-stage") \
                        .style(_fitted(*self._design.canvas()))
                    ui.label("Click a piece to pick it, drag it, pull its corner to make it bigger. Arrow keys move "
                             "it (Shift: ten pixels), Delete removes it, Ctrl+D copies it, Ctrl+Z undoes. It snaps "
                             "to the middle and edges of the canvas and of the other pieces (hold Alt not to). "
                             "Saved by itself. A value nobody filled yet shows "
                             "TestViewer here; on stream it stays empty until then.") \
                        .classes("text-xs opacity-60 self-stretch")
                self._preview_box = ui.column().classes("w-full gap-2 items-center")
                self._preview_box.set_visibility(False)
            with ui.column().classes("tb-design-side order-3 w-full lg:w-[26rem] shrink-0 gap-2"):
                with ui.card().classes("w-full gap-1 p-3"):
                    self._layers()
                with ui.card().classes("w-full gap-1 p-3"):
                    self._pieces()
                with ui.card().classes("w-full gap-2 p-3"):
                    self._panel()
        ui.on(self._event, self._from_stage)
        ui.timer(0.2, self._save_when_quiet)
        ui.timer(0.1, self._draw, once=True)

    # the parts of the page

    @ui.refreshable_method
    def _undo_buttons(self) -> None:
        ui.button(icon="undo", on_click=self._do_undo).props("flat round dense") \
            .tooltip("Undo (Ctrl+Z)").set_enabled(bool(self._undo))
        ui.button(icon="redo", on_click=self._do_redo).props("flat round dense") \
            .tooltip("Redo (Ctrl+Y)").set_enabled(bool(self._redo))

    @ui.refreshable_method
    def _layer_bar(self) -> None:
        layers = dict(reversed(self._design.layers()))
        alert = bool(self._design.event_of(self._layer))
        with ui.row().classes("w-full items-center gap-2"):
            ui.select(layers, value=self._layer, label="Editing the layer",
                      on_change=lambda e: self._pick_layer(e.value)) \
                .props("outlined dense options-dense").classes("w-56") \
                .tooltip("Add, rename, reorder and delete layers in the Layers list")
            ui.label(f"An alert for: {EVENT_NAMES.get(self._design.event_of(self._layer), '?')}" if alert
                     else "Always there").classes("text-sm opacity-70")

    @ui.refreshable_method
    def _add_list(self) -> None:
        DesignAddList(bool(self._design.event_of(self._layer)), self._add).build()

    @ui.refreshable_method
    def _layers(self) -> None:
        DesignLayerPanel(self._design, self._layer, self._windows, self._pick_layer, self._layer_do,
                         self._remove_layer).build()

    @ui.refreshable_method
    def _pieces(self) -> None:
        pieces = self._design.pieces(self._layer)
        ui.label("Pieces of this layer, the top one in front").classes("text-sm font-semibold")
        if not pieces:
            ui.label("None yet: add one from the list on the left.").classes("text-sm opacity-70")
        for name in reversed(list(pieces)):
            kind = pieces[name].get("type")
            picked = name == self._picked
            with ui.row().classes("w-full items-center no-wrap gap-1 rounded px-1 cursor-pointer "
                                  + ("bg-primary/20" if picked else "hover:bg-gray-500/10")) \
                    .on("click", lambda n=name: self._pick(n)):
                ui.icon(ICONS.get(kind, "help"), size="xs").classes("opacity-70")
                ui.label(name).classes("flex-1 min-w-0 truncate text-sm")
                if picked:
                    for icon, tip, step in (("arrow_upward", "Forward", 1), ("arrow_downward", "Back", -1)):
                        ui.button(icon=icon, on_click=lambda s=step: self._restack(s)) \
                            .props("flat round dense size=sm").tooltip(tip)
                    ui.button(icon="content_copy", on_click=self._duplicate).props("flat round dense size=sm") \
                        .tooltip("Copy it")
                    ui.button(icon="delete", on_click=lambda: self._remove(self._picked)) \
                        .props("flat round dense size=sm").tooltip("Remove it (Delete)")

    @ui.refreshable_method
    def _panel(self) -> None:
        if not self._picked or self._picked not in self._design.pieces(self._layer):
            ui.label("Pick a piece on the canvas or in the list to change it.").classes("text-sm opacity-70")
            return
        DesignPiecePanel(self._design, self._layer, self._picked, self._change, self._pick_file, self._uploaded,
                         self._try_reaction, self._align).build()

    def _show_mode(self, mode: str) -> None:
        self._edit_box.set_visibility(mode == "edit")
        self._preview_box.set_visibility(mode == "preview")
        if mode == "preview":
            self._save_now()
            self._preview_box.clear()
            with self._preview_box:
                self._preview()
        else:
            self._draw()

    def _preview(self) -> None:
        width, height = self._design.canvas()
        box, frame = f"box_{uuid.uuid4().hex[:8]}", f"frame_{uuid.uuid4().hex[:8]}"
        with ui.element("div").props(f"id={box}").classes("tb-design-stage").style(_fitted(width, height)):
            ui.element("iframe").props(f"id={frame} src=/overlay/widget/{self._name}?preview=1 allow=autoplay") \
                .style(f"width: {width}px; height: {height}px; border: 0; display: block; "
                       "transform-origin: top left; color-scheme: light")
        ui.run_javascript(f"""
            (() => {{
                const box = document.getElementById("{box}"), frame = document.getElementById("{frame}");
                if (!box || !frame) return;
                const fit = () => {{ frame.style.transform = "scale(" + box.clientWidth / {width} + ")"; }};
                new ResizeObserver(fit).observe(box);
                fit();
            }})();""")
        with ui.row().classes("items-center gap-2"):
            ui.label("Test:").classes("text-sm opacity-70")
            for event, name in EVENT_NAMES.items():
                if event != "communityGiftPurchase":
                    ui.button(name, on_click=lambda e=event: self._hub.test(self._name, TEST_LISTENERS[e])) \
                        .props("no-caps outline dense")
        ui.label("The widget as OBS shows it. A test event plays here and in OBS; nothing is saved from it.") \
            .classes("text-xs opacity-60")

    # the canvas

    def _draw(self) -> None:
        if self._mode.value != "edit":
            return
        width, height = self._design.canvas()
        data = {"width": width, "height": height, "pieces": self._stage_pieces(), "selected": self._picked}
        fonts = sorted(self._fonts())
        ui.run_javascript(
            "for (const href of %s) { if (!document.querySelector(`link[href=\"${href}\"]`)) { "
            "const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = href; "
            "document.head.append(link); } } TOOLBOX_DESIGNER.show(%s, %s, %s);"
            % (json.dumps(fonts), json.dumps(self._stage), json.dumps(self._event),
               json.dumps(data, ensure_ascii=False)))

    def _stage_pieces(self) -> list[dict[str, Any]]:
        """What the canvas draws, stacked as element.js stacks them: the layers that are always there and on,
        and the one being edited (an alert's: the other alerts don't show, they come one at a time)."""
        states = self._design.config["configStates"]
        editing_alert = bool(self._design.event_of(self._layer))
        shown = [n for n in range(len(states)) if n == self._layer
                 or (not self._design.event_of(n) and self._design.is_on(n))]
        shown.sort(key=self._z)
        session = self._hub.session.data
        drawn = []
        for number in shown:
            mine = number == self._layer
            for name, piece in self._design.pieces(number).items():
                kind = DRAWN.get(piece.get("type"))
                if kind is None:
                    continue
                entry = {"id": name if mine else f"{number}:{name}", "kind": kind, "editable": mine,
                         "resize": RESIZE.get(piece.get("type"), "width"),
                         "style": {k: v for k, v in (piece.get("style") or {}).items()
                                   if isinstance(v, (str, int, float))}}
                ticker = self._design.ticker(number, name) if piece.get("type") == "latestTicker" else None
                if ticker:
                    entry["parts"] = DesignValues.ticker(ticker, session)
                    entry["highlight"] = piece.get("highlightedStyle") or {}
                elif kind == "text":
                    entry["parts"] = DesignValues.fill(self._design.text(number, name), session)
                    entry["highlight"] = piece.get("highlightedStyle") or {}
                elif kind == "goal":
                    goal = self._design.goal(number, name)
                    count = DesignValues.fill(f"{{session.twitch.{goal['value']}}}", session)[0][0]
                    value = float(count) if count.replace(".", "", 1).isdigit() else 0
                    percent = min(100, int(value / max(float(goal["target"]), 1) * 100))
                    entry["percent"] = percent
                    entry["fill"] = piece.get("fillStyle") or {}
                    entry["label"] = goal["label"].replace("{value}", f"{value:g}") \
                        .replace("{target}", f"{float(goal['target']):g}").replace("{percent}", f"{percent}%")
                elif kind == "shape":
                    pass
                else:
                    href = self._design.file(number, name)
                    entry["src"] = self._media_address(href) if href else ""
                if not mine and editing_alert:
                    entry["style"]["opacity"] = "0.5"
                drawn.append(entry)
        return drawn

    def _z(self, number: int) -> int:
        """Behind the alerts (1, 2), an alert (3), in front of them (4): element.js's stacking."""
        if self._design.event_of(number):
            return 3
        if self._design.in_front(number):
            return 4
        return 1 if self._design.config["configStates"][number].get("referenceId") == "background" else 2

    def _media_address(self, href: str) -> str:
        if href.startswith(("http://", "https://", "//", "/")):
            return href
        return f"/overlay/widget/{self._name}/media/{href}"

    def _fonts(self) -> set[str]:
        found = set()
        for state in self._design.config["configStates"]:
            for piece in ((state.get("settings") or {}).get("compositeFields") or {}).values():
                for media in piece.get("media") or []:
                    if media.get("role") == "font-face" and media.get("href"):
                        found.add(self._media_address(str(media["href"])))
        return found

    def _from_stage(self, e) -> None:
        what = e.args or {}
        do, name = what.get("do"), str(what.get("id") or "")
        if do == "select":
            self._pick(name if name in self._design.pieces(self._layer) else "")
        elif do == "move" and name in self._design.pieces(self._layer):
            self._change(f"move/{name}", lambda d: d.move(self._layer, name, float(what["left"]), float(what["top"])),
                         whole=True, group=False)
        elif do == "resize" and name in self._design.pieces(self._layer):
            font, height = what.get("fontSize"), what.get("height")
            self._change(f"size/{name}", lambda d: d.resize(self._layer, name, float(what["width"]),
                                                            float(font) if font else None,
                                                            float(height) if height else None),
                         whole=True, group=False)
        elif do == "duplicate" and name in self._design.pieces(self._layer):
            self._picked = name
            self._duplicate()
        elif do == "delete" and name in self._design.pieces(self._layer):
            self._remove(name)
        elif do == "undo":
            self._do_undo()
        elif do == "redo":
            self._do_redo()

    # changes

    def _change(self, key: str, what, whole: bool = False, group: bool = True) -> None:
        """Changes the design (what(design)); one undo step per run of changes to the same thing (typing a
        text is one step). whole: the lists and the panel are drawn again too (else only the canvas: an input
        being typed in keeps its focus)."""
        if not group or key != self._last_key:
            self._remember()
        self._last_key = key if group else ""
        try:
            result = what(self._design)
        except (ValueError, KeyError) as error:
            ui.notify(str(error), type="warning")
            return
        if key == "rename" and isinstance(result, str):
            self._picked, whole = result, True
        self._changed(whole)

    def _remember(self) -> None:
        self._undo.append((self._design.copy(), self._layer, self._picked))
        del self._undo[:-UNDO_STEPS]
        self._redo.clear()
        self._undo_buttons.refresh()

    def _changed(self, whole: bool = True) -> None:
        self._dirty = True
        self._quiet = 0.0
        self._draw()
        if whole:
            self._layers.refresh()
            self._pieces.refresh()
            self._panel.refresh()
            self._layer_bar.refresh()
            self._add_list.refresh()

    def _do_undo(self) -> None:
        self._step(self._undo, self._redo)

    def _do_redo(self) -> None:
        self._step(self._redo, self._undo)

    def _step(self, source: list, target: list) -> None:
        if not source:
            return
        target.append((self._design.copy(), self._layer, self._picked))
        self._design, self._layer, self._picked = source.pop()
        self._last_key = ""
        self._undo_buttons.refresh()
        self._changed()

    def _pick(self, name: str) -> None:
        if name == self._picked:
            return
        self._picked = name
        self._last_key = ""
        self._draw()
        self._pieces.refresh()
        self._panel.refresh()

    def _pick_layer(self, layer: int) -> None:
        if layer == self._layer:
            return
        self._layer, self._picked, self._last_key = layer, "", ""
        self._draw()
        self._layers.refresh()
        self._pieces.refresh()
        self._panel.refresh()
        self._layer_bar.refresh()
        self._add_list.refresh()

    def _layer_do(self, key: str, what) -> None:
        """A change to the layers (DesignLayerPanel): what(design) gives the layer to edit next, or None for the
        same one. A key groups a run of changes (typing a number) into one undo step."""
        if not key or key != self._last_key:
            self._remember()
        self._last_key = key
        try:
            layer = what(self._design)
        except (ValueError, KeyError) as error:
            ui.notify(str(error), type="warning")
            return
        if isinstance(layer, int) and layer != self._layer:
            self._layer, self._picked = layer, ""
        self._layer = min(self._layer, len(self._design.layers()) - 1)
        self._changed(whole=not key)  # a number being typed keeps its focus

    async def _remove_layer(self, layer: int) -> None:
        title = dict(self._design.layers())[layer]
        count = len(self._design.pieces(layer))
        if len(self._design.layers()) == 1:
            ui.notify("A widget keeps one layer at least (it can be empty)", type="warning")
            return
        with self._windows, ui.dialog() as dialog, ui.card().classes("w-96 gap-3"):
            ui.label(f"Delete the layer {title}?").classes("text-lg font-semibold")
            ui.label(f"Its {count} piece{'' if count == 1 else 's'} go with it (Undo brings them back). The files "
                     "stay in the widget's media folder.").classes("text-sm opacity-80")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Delete", on_click=lambda: dialog.submit(True)).props("unelevated no-caps color=negative")
        sure = await dialog
        dialog.delete()
        if not sure:
            return
        self._remember()
        self._design.remove_layer(layer)
        if self._layer >= layer:
            self._layer, self._picked = max(self._layer - 1, 0), "" if self._layer == layer else self._picked
        self._changed()

    def _add(self, preset: DesignPreset) -> None:
        self._remember()
        self._picked = preset.add_to(self._design, self._layer)
        self._last_key = ""
        self._changed()

    def _remove(self, name: str) -> None:
        self._remember()
        self._design.remove(self._layer, name)
        self._picked = "" if self._picked == name else self._picked
        self._changed()

    def _duplicate(self) -> None:
        self._remember()
        self._picked = self._design.duplicate(self._layer, self._picked)
        self._changed()

    def _restack(self, step: int) -> None:
        self._remember()
        self._design.restack(self._layer, self._picked, step)
        self._changed()

    def _align(self, how: str) -> None:
        ui.run_javascript(f"TOOLBOX_DESIGNER.align({json.dumps(self._stage)}, {json.dumps(how)})")

    async def _canvas_size(self) -> None:
        width, height = self._design.canvas()
        with self._windows, ui.dialog() as dialog, ui.card().classes("w-96 gap-3"):
            ui.label("The widget's size").classes("text-lg font-semibold")
            ready = ui.select(SIZES, label="A usual one", on_change=lambda e: e.value and (
                wide.set_value(int(e.value.split("x")[0])), high.set_value(int(e.value.split("x")[1])))) \
                .props(FIELD).classes("w-full")
            with ui.row().classes("w-full no-wrap gap-2"):
                wide = ui.number("Width", value=width, min=50, max=7680, step=10).props(FIELD).classes("flex-1")
                high = ui.number("Height", value=height, min=50, max=4320, step=10).props(FIELD).classes("flex-1")
            ready.set_value(f"{width}x{height}" if f"{width}x{height}" in SIZES else None)
            ui.label("Give OBS's Browser source the same size. The pieces stay where they are: one outside the "
                     "new size isn't seen.").classes("text-xs opacity-60")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Set", on_click=lambda: dialog.submit(True)).props("unelevated no-caps")
        sure = await dialog
        dialog.delete()
        if sure and wide.value and high.value and (int(wide.value), int(high.value)) != (width, height):
            self._remember()
            self._design.set_canvas(int(wide.value), int(high.value))
            self._changed()

    # files

    async def _pick_file(self) -> None:
        kind = self._design.piece(self._layer, self._picked).get("type")
        endings = tuple(ending for ending, mime in ENDINGS.items() if mime.startswith(f"{kind}/"))
        with self._windows:
            path = await FileDialog(endings).open()
        if not path:
            return
        try:
            content = Path(path).read_bytes()
        except OSError as error:
            ui.notify(f"Can't read it: {error}", type="negative")
            return
        self._take_file(Path(path).name, content)

    async def _uploaded(self, e) -> None:
        self._take_file(e.file.name, await e.file.read())

    def _take_file(self, file_name: str, content: bytes) -> None:
        name, layer = self._picked, self._layer
        try:
            stored = self._files.add(self._name, file_name, content)
        except (KeyError, ValueError, OSError) as error:
            ui.notify(f"Not added: {error}", type="negative")
            return
        self._change("file", lambda d: d.set_file(layer, name, stored), whole=True, group=False)

    def _try_reaction(self, events: list[str]) -> None:
        if not events:
            ui.notify("Pick an event first", type="warning")
            return
        self._mode.set_value("preview")
        ui.timer(1.5, lambda: self._hub.test(self._name, TEST_LISTENERS[events[0]]), once=True)

    # saving

    def _save_when_quiet(self) -> None:
        if not self._dirty:
            return
        self._quiet += 0.2
        if self._quiet >= SAVE_AFTER:
            self._save_now()

    def _save_now(self) -> None:
        if not self._dirty:
            return
        self._dirty = False
        widget = self._store.get(self._name)
        if widget is None:
            ui.notify(f"The widget {self._name} isn't there any more: not saved", type="negative")
            return
        self._store.save(replace(widget, js=self._design.to_js()))
        # the event types its alerts and reactions need, besides the ones it had (their flows made once)
        needed = [kind for event in sorted(self._design.events()) for kind in EVENT_TYPES[event]]
        if set(needed) - set(widget.events or ()):
            self._users.set_widget_events(self._name, (*(widget.events or ()), *needed))
        self._hub.reload(self._name)
