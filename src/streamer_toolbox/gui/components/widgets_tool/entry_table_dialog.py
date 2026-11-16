import json
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from nicegui import ui

from streamer_toolbox.core.widgets.design_values import DesignValues
from streamer_toolbox.core.widgets.element_design import ENDINGS, LIST_EVENTS, ElementDesign
from streamer_toolbox.core.widgets.element_settings import _number
from streamer_toolbox.core.widgets.entry_table import CELL_KINDS, FITS, LAYER_KINDS, LAYERS, EntryTable
from streamer_toolbox.gui.components.widgets_tool.emoji_help import EMOJI_HELP

FIELD = "outlined dense options-dense"
# the arrow buttons: side → (icon, words)
SIDES = {"top": ("north", "above", "up"), "right": ("east", "right of", "to the right"),
         "bottom": ("south", "below", "down"), "left": ("west", "left of", "to the left")}
# where each arrow sits in its 3x3 cross: (column, row)
CROSS = {"top": (2, 1), "right": (3, 2), "bottom": (2, 3), "left": (1, 2)}
CELL_ICONS = {"text": "title", "image": "image", "video": "movie"}
FONTS = ["Arial", "Arial Black", "Verdana", "Tahoma", "Trebuchet MS", "Segoe UI", "Georgia", "Times New Roman",
         "Courier New", "Impact", "Comic Sans MS", "Consolas"]
# what the preview fills in besides the values' defaults: a chat message's own words
SAMPLES = {"message": {"message": "Hello chat Kappa how is everyone?"}}
# the preview's emoji dictionary for a text that has one (the event's own on stream)
SAMPLE_EMOJI = {"Kappa": "https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/3.0"}

# what each layer is for (his round 90)
LAYER_TIPS = {"back": "A picture or video behind the whole entry, under its cells: e.g. every event's own background",
              "front": "A picture or video over the whole entry: e.g. a glass or a frame (a PNG with see-through "
                       "parts)"}

# change(key, what, whole=..., group=...): WidgetDesigner._change
Change = Callable[..., None]


class EntryTableDialog:
    """How one event looks in an event list (his round 89: "you can add to the top, right, left, bottom of the
    text, like a table where you can combine cells; you can add picture, video, text to every cell"): the table
    of cells on the left (click one to pick it; arrows add a cell on that side, move what it holds there or
    join it with the cells there), the picked cell's settings on the right (what it holds, its look), the look
    of the whole entry, a layer behind it and one in front (his round 90), and a preview drawn by
    event_entry.js, as OBS draws it. The values a text or an
    address can have are that event's own, by their names as Overlay → Events has them ({user}; his 11-13:
    "1to1 the same name as the event values"): `values`, DesignValues.list_values. Every change goes through
    the editor's undo."""

    def __init__(self, design: ElementDesign, layer: int, name: str, event: str, change: Change,
                 windows: ui.element, take_file: Callable[[str, bytes], str | None], media: Callable[[str], str],
                 pick_file: Callable[[tuple[str, ...]], Awaitable[tuple[str, bytes] | None]],
                 values: list[dict[str, Any]]) -> None:
        self._design = design
        self._layer = layer
        self._name = name
        self._event = event
        self._change = change
        self._windows = windows
        self._take_file = take_file
        self._media = media
        self._pick_file = pick_file
        self._picked = 0
        self._values = values
        self._preview_id = f"entry_{uuid.uuid4().hex[:8]}"

    def _table(self) -> EntryTable:
        return self._design.list_entry(self._layer, self._name, self._event)

    async def open(self) -> None:
        with self._windows, ui.dialog() as dialog, \
                ui.card().classes("w-[64rem] max-w-full gap-3"):
            with ui.row().classes("w-full items-center"):
                ui.label(f"How a {LIST_EVENTS[self._event].casefold()} looks in the list") \
                    .classes("text-lg font-semibold")
                ui.space()
                ui.button(icon="close", on_click=dialog.close).props("flat round dense").tooltip("Done")
            with ui.element("div").classes("w-full flex flex-col md:flex-row gap-4 items-start"):
                with ui.column().classes("w-full md:flex-1 min-w-0 gap-2"):
                    ui.label("Click a cell to pick it.").classes("text-xs opacity-60")
                    self._grid()
                    self._tools()
                    ui.label("Preview").classes("text-sm font-semibold pt-2")
                    ui.element("div").props(f"id={self._preview_id}") \
                        .classes("w-full p-3 rounded overflow-auto") \
                        .style("display: flex; align-items: flex-start; background: repeating-conic-gradient("
                               "#80808033 0 25%, transparent 0 50%) 0 0 / 20px 20px")
                    ui.label("Example values; on stream each event's own. Pictures and videos show here too.") \
                        .classes("text-xs opacity-60")
                with ui.column().classes("w-full md:w-80 shrink-0 gap-2"):
                    self._cell_panel()
                    with ui.expansion("The whole entry", icon="crop_free").classes("w-full") \
                            .props("dense header-class=px-0"):
                        self._entry_panel()
                    with ui.expansion("Behind and in front", icon="layers").classes("w-full") \
                            .props("dense header-class=px-0"):
                        self._layers_panel()
            with ui.row().classes("w-full justify-end"):
                ui.button("Done", on_click=dialog.close).props("unelevated no-caps")
        dialog.on("show", self._preview)
        dialog.open()
        ui.timer(0.2, self._preview, once=True)
        await dialog
        dialog.delete()

    # the table

    @ui.refreshable_method
    def _grid(self) -> None:
        table = self._table()
        with ui.element("div").classes("w-full").style(
                f"display: grid; grid-template-columns: repeat({table.data['columns']}, minmax(70px, auto)); "
                "gap: 4px"):
            for number, cell in enumerate(table.cells()):
                picked = number == self._picked
                with ui.element("div").classes(
                        "rounded p-2 cursor-pointer border min-w-0 flex items-center gap-1 "
                        + ("border-primary bg-primary/20" if picked else "border-gray-500/40 hover:bg-gray-500/10")) \
                        .style(f"grid-column: {cell['col'] + 1} / span {cell['cols']}; "
                               f"grid-row: {cell['row'] + 1} / span {cell['rows']}; min-height: 44px") \
                        .on("click", lambda n=number: self._pick(n)):
                    ui.icon(CELL_ICONS.get(cell["kind"], "help"), size="xs").classes("opacity-60 shrink-0")
                    words = cell["text"] if cell["kind"] == "text" \
                        else cell["address"] or cell["file"] or CELL_KINDS[cell["kind"]]
                    ui.label(words or "(empty)").classes("text-sm min-w-0 break-words" + ("" if words else " opacity-50"))
            for col, row in table.empty_spots():
                with ui.element("div").classes(
                        "rounded border border-dashed border-gray-500/40 cursor-pointer flex items-center "
                        "justify-center opacity-60 hover:bg-gray-500/10") \
                        .style(f"grid-column: {col + 1}; grid-row: {row + 1}; min-height: 44px") \
                        .on("click", lambda c=col, r=row: self._edit("put", lambda t: self._put(t, c, r))) \
                        .tooltip("Empty: nothing shows here. Click: a new cell here"):
                    ui.icon("add", size="xs")

    @ui.refreshable_method
    def _tools(self) -> None:
        """Add, move and join: each its four arrows in a cross, the three side by side."""
        with ui.row().classes("w-full items-end gap-4"):
            for title, key, does, tip in (
                    ("Add a cell", "add", self._added,
                     "A new cell {words} the picked one (on the empty spot there, else in a new {line})"),
                    ("Move it", "move", self._moved,
                     "It goes one {line} {way}; what is there takes its old place (or gets smaller when it is "
                     "bigger)"),
                    ("Join with", "join", self._joined,
                     "It grows over the next {line} {way}; what is there goes or gets smaller (it keeps what it "
                     "holds)")):
                with ui.column().classes("items-center gap-0"):
                    ui.label(title).classes("text-xs opacity-70")
                    with ui.element("div").style("display: grid; grid-template-columns: repeat(3, 2rem); "
                                                 "grid-template-rows: repeat(3, 2rem); place-items: center"):
                        for side, (icon, words, way) in SIDES.items():
                            line = "column" if side in ("left", "right") else "row"
                            spot = CROSS[side]
                            ui.button(icon=icon, on_click=lambda k=key, d=does, s=side: self._edit(
                                k, lambda t: d(t, s))).props("flat round dense") \
                                .style(f"grid-column: {spot[0]}; grid-row: {spot[1]}") \
                                .tooltip(tip.format(words=words, way=way, line=line))
            ui.space()
            ui.button("Remove cell", icon="delete", on_click=lambda: self._edit("remove", self._removed)) \
                .props("flat dense no-caps")

    def _added(self, table: EntryTable, side: str) -> None:
        self._picked = table.add(self._picked, side)

    def _moved(self, table: EntryTable, side: str) -> None:
        self._picked = table.move(self._picked, side)

    def _put(self, table: EntryTable, col: int, row: int) -> None:
        self._picked = table.put(col, row)

    def _joined(self, table: EntryTable, side: str) -> None:
        cell = table.cell(self._picked)
        table.join(self._picked, side)
        self._picked = next(number for number, each in enumerate(table.cells()) if each is cell)

    def _removed(self, table: EntryTable) -> None:
        table.remove(self._picked)
        self._picked = 0

    def _pick(self, number: int) -> None:
        self._picked = number
        self._grid.refresh()
        self._cell_panel.refresh()

    # the picked cell

    @ui.refreshable_method
    def _cell_panel(self) -> None:
        table = self._table()
        self._picked = min(self._picked, len(table.cells()) - 1)
        cell = table.cell(self._picked)
        style = cell.get("style") or {}
        ui.label("The picked cell").classes("text-sm font-semibold")
        ui.toggle({kind: title for kind, title in CELL_KINDS.items()}, value=cell["kind"],
                  on_change=lambda e: e.value != cell["kind"] and self._edit(
                      "kind", lambda t: t.set_cell(self._picked, kind=e.value))) \
            .props("dense no-caps spread").classes("w-full flex-wrap")
        if cell["kind"] == "text":
            box = ui.textarea("Text", value=cell["text"],
                              on_change=lambda e: self._edit(f"text/{self._picked}", lambda t: t.set_cell(
                                  self._picked, text=e.value or ""), whole=False)) \
                .props(FIELD + " autogrow").classes("w-full")
            self._value_list(box, " ")
            self._emoji(cell)
        else:
            box = ui.input("Address", value=cell["address"],
                           on_change=lambda e: self._edit(f"address/{self._picked}", lambda t: t.set_cell(
                               self._picked, address=e.value or ""), whole=False)) \
                .props(FIELD + " clearable").classes("w-full")
            self._value_list(box, "")
            picked = self._picked
            self._file_choice(cell, lambda t, f: t.set_cell(picked, file=f, address="") if f
                              else t.set_cell(picked, file=""))
        ui.label("Its look").classes("text-sm font-semibold pt-1")
        with ui.row().classes("w-full no-wrap gap-2"):
            for key, label in (("width", "Width"), ("height", "Height")):
                ui.number(label, value=_number(style.get(key)), min=0, step=1, suffix="px",
                          on_change=lambda e, k=key: self._style(k, f"{e.value}px" if e.value else None)) \
                    .props(FIELD + " clearable").classes("flex-1 min-w-0").tooltip("Empty: as much as it needs")
        with ui.row().classes("w-full items-center gap-2"):
            ui.toggle({"left": "Left", "center": "Middle", "right": "Right"},
                      value=str(style.get("textAlign") or "left"),
                      on_change=lambda e: self._style("textAlign", e.value)) \
                .props("dense no-caps")
            ui.toggle({"start": "Top", "center": "Middle", "end": "Bottom"}, value=str(style.get("alignSelf") or "center"),
                      on_change=lambda e: self._style("alignSelf", e.value)).props("dense no-caps") \
                .tooltip("Up and down in its row")
        if cell["kind"] == "text":
            self._words_look(style, lambda key, value: self._style(key, value))
        with ui.row().classes("w-full no-wrap gap-2"):
            self._colour("Background", style.get("backgroundColor"),
                         lambda value: self._style("backgroundColor", value))
            ui.number("Corners", value=_number(style.get("borderRadius")) or 0, min=0, step=2,
                      on_change=lambda e: self._style("borderRadius", f"{e.value}px" if e.value else None)) \
                .props(FIELD).classes("w-24").tooltip("50 or more on a square picture: a circle")
        ui.number("Inner space", value=_number(style.get("padding")) or 0, min=0, step=1, suffix="px",
                  on_change=lambda e: self._style("padding", f"{e.value}px" if e.value else None)) \
            .props(FIELD).classes("w-full")

    def _emoji(self, cell: dict[str, Any]) -> None:
        """His 2026-11-16: the text's emoji dictionary (a value of the event) and how high its pictures are."""
        names = {"": "Nothing", **{name: name for name in self._names()}}
        if cell["emoji_dict"] and cell["emoji_dict"] not in names:
            names[cell["emoji_dict"]] = f"{cell['emoji_dict']} (the event has no such value)"
        with ui.row().classes("w-full no-wrap items-center gap-2"):
            ui.select(names, value=cell["emoji_dict"], label="Emoji dictionary",
                      on_change=lambda e: self._edit("emoji", lambda t: t.set_cell(
                          self._picked, emoji_dict=e.value or ""))).props(FIELD).classes("flex-1 min-w-0") \
                .tooltip("The event's value that holds the emoji dictionary (emoji_dict)")
            if cell["emoji_dict"]:
                ui.number("Emoji size", value=cell["emoji_size"] or None, min=0, step=1, suffix="px",
                          on_change=lambda e: self._edit("emoji_size", lambda t: t.set_cell(
                              self._picked, emoji_size=e.value or 0), whole=False)) \
                    .props(FIELD + " clearable").classes("w-28").tooltip("Empty: as high as the words")
        with ui.expansion("How the emoji dictionary works", icon="info").classes("w-full text-xs") \
                .props("dense header-class='px-0 text-xs opacity-70'"):
            ui.markdown(EMOJI_HELP).classes("text-xs")

    def _value_list(self, box: ui.input, before: str) -> None:
        """Adds the value picked in it to the box (a text or an address)."""
        def add_value(e) -> None:
            if e.value:
                box.set_value((box.value or "").rstrip(" ") + (before if box.value else "") + f"{{{e.value}}}")
                e.sender.set_value(None)
        ui.select(self._names(), label="Add a value", on_change=add_value) \
            .props(FIELD).classes("w-full").tooltip(f"Filled in with each {LIST_EVENTS[self._event].casefold()}'s "
                                                    "own. The values and their names: Overlay → Events")

    def _names(self) -> list[str]:
        """The values a text, an address or a colour can have: the event's own (Overlay → Events)."""
        return [value["name"] for value in self._values]

    def _colour(self, label: str, value: Any, set_: Callable[[Any], None]) -> None:
        """A colour: picked, typed, or one of the event's values ({color}; the bolt's list). A value that is
        empty for an event (no colour picked) leaves the colour of the whole entry."""
        field = ui.color_input(label, value=str(value or ""), on_change=lambda e: set_(e.value or None)) \
            .props(FIELD).classes("flex-1 min-w-0").tooltip("A colour, or a value of the event: {color}")
        with ui.button(icon="bolt").props("flat round dense size=sm").classes("-ml-2") \
                .tooltip(f"{label}: a value of the event"):
            with ui.menu():
                for name in self._names():
                    ui.menu_item(name, on_click=lambda n=name: field.set_value(f"{{{n}}}"))

    def _words_look(self, style: dict[str, Any], set_: Callable[[str, Any], None]) -> None:
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.select(sorted({*FONTS, str(style.get("fontFamily") or "Arial")}), label="Font",
                      value=str(style.get("fontFamily") or "Arial"), new_value_mode="add-unique",
                      on_change=lambda e: set_("fontFamily", e.value)).props(FIELD + " use-input") \
                .classes("flex-1 min-w-0")
            ui.number("Size", value=_number(style.get("fontSize")) or None, min=1, step=1,
                      on_change=lambda e: set_("fontSize", f"{e.value}px" if e.value else None)) \
                .props(FIELD).classes("w-24")
        with ui.row().classes("w-full no-wrap items-center gap-2"):
            self._colour("Colour", style.get("color"), lambda value: set_("color", value))
            ui.switch("Bold", value=str(style.get("fontWeight") or "") in ("bold", "700", "800", "900"),
                      on_change=lambda e: set_("fontWeight", "bold" if e.value else None)).props("dense")
            ui.switch("Shadow", value=bool(style.get("textShadow")),
                      on_change=lambda e: set_("textShadow", "2px 2px 4px #000000" if e.value else None)) \
                .props("dense")

    def _style(self, key: str, value: Any) -> None:
        self._edit(f"style/{self._picked}/{key}", lambda t: t.set_style(self._picked, **{key: value}), whole=False)

    # the whole entry

    def _entry_panel(self) -> None:
        style = self._table().data.get("style") or {}

        def set_(key: str, value: Any) -> None:
            self._edit(f"entry/{key}", lambda t: t.set_style(None, **{key: value}), whole=False)
        with ui.row().classes("w-full no-wrap gap-2"):
            self._colour("Background", style.get("backgroundColor"), lambda value: set_("backgroundColor", value))
            ui.number("Corners", value=_number(style.get("borderRadius")) or 0, min=0, step=2,
                      on_change=lambda e: set_("borderRadius", f"{e.value}px" if e.value else None)) \
                .props(FIELD).classes("w-24")
        with ui.row().classes("w-full no-wrap gap-2"):
            ui.number("Inner space", value=_number(str(style.get("padding") or "0").split()[0]) or 0, min=0, step=1,
                      suffix="px", on_change=lambda e: set_("padding", f"{e.value}px" if e.value else None)) \
                .props(FIELD).classes("flex-1 min-w-0")
            ui.number("Between cells", value=_number(style.get("gap")) if style.get("gap") else 6, min=0, step=1,
                      suffix="px", on_change=lambda e: set_("gap", f"{e.value or 0}px")) \
                .props(FIELD).classes("flex-1 min-w-0")
        ui.number("Width", value=_number(style.get("width")), min=0, step=1, suffix="px",
                  on_change=lambda e: set_("width", f"{e.value}px" if e.value else None)) \
            .props(FIELD + " clearable").classes("w-full").tooltip("Empty: as wide as it needs; in a list that goes "
                                                                    "up or down, the whole width: type it")
        ui.label("The words (a cell's own look comes first)").classes("text-xs opacity-70 pt-1")
        self._words_look(style, set_)

    # behind and in front

    @ui.refreshable_method
    def _layers_panel(self) -> None:
        table = self._table()
        for side, title in LAYERS.items():
            own = table.layer(side)
            ui.label(title).classes("text-sm font-semibold pt-1").tooltip(LAYER_TIPS[side])
            ui.toggle({"none": "Nothing", **LAYER_KINDS}, value=own["kind"] if own else "none",
                      on_change=lambda e, s=side, o=own: e.value != (o["kind"] if o else "none") and self._edit(
                          f"layer/{s}", lambda t: t.set_layer(s, kind="" if e.value == "none" else e.value))) \
                .props("dense no-caps spread").classes("w-full flex-wrap")
            if not own:
                ui.label(LAYER_TIPS[side] + ".").classes("text-xs opacity-60")
                continue
            box = ui.input("Address", value=own["address"],
                           on_change=lambda e, s=side: self._edit(f"layer/{s}/address", lambda t: t.set_layer(
                               s, address=e.value or ""), whole=False)) \
                .props(FIELD + " clearable").classes("w-full")
            self._value_list(box, "")
            self._file_choice(own, lambda t, f, s=side: t.set_layer(s, file=f, address="") if f
                              else t.set_layer(s, file=""))
            with ui.row().classes("w-full no-wrap items-center gap-2"):
                ui.select(FITS, value=own["fit"], label="Fits",
                          on_change=lambda e, s=side: self._edit(f"layer/{s}/fit", lambda t: t.set_layer(
                              s, fit=e.value), whole=False)).props(FIELD).classes("w-40 shrink-0")
                ui.label("See-through").classes("text-xs opacity-70 shrink-0")
                ui.slider(min=0, max=100, step=5, value=round((1 - own["opacity"]) * 100),
                          on_change=lambda e, s=side: self._edit(f"layer/{s}/opacity", lambda t: t.set_layer(
                              s, opacity=round(1 - (e.value or 0) / 100, 2)), whole=False)) \
                    .props("label").classes("flex-1")

    # files

    def _file_choice(self, own: dict[str, Any], put: Callable[[EntryTable, str], Any]) -> None:
        """A cell's or a layer's file of the widget: picked on the PC or sent from this device. put(table, file)
        sets it ("" for none)."""
        kind = own["kind"]
        ui.label("A web address (https://...), a path on this PC (C:\\Pictures\\{user}.png) or in the "
                 "toolbox's folder (pictures\\cat.gif), with values in it.").classes("text-xs opacity-60")
        ui.label(f"Or a file: {own['file']}" + (" (the address comes first)" if own["address"] else "")
                 if own["file"] else "Or a file of the widget:").classes("text-xs break-all")
        with ui.row().classes("w-full items-center gap-2"):
            ui.button("Pick a file on the PC", icon="folder_open",
                      on_click=lambda: self._file_from_pc(kind, put)).props("no-caps outline dense")
            if own["file"]:
                ui.button(icon="close", on_click=lambda: self._edit("file", lambda t: put(t, ""))) \
                    .props("flat round dense").tooltip("No file")
        accept = "image/*" if kind == "image" else "video/webm,video/mp4"

        async def uploaded(e) -> None:
            self._use_file(e.file.name, await e.file.read(), put)
        ui.upload(on_upload=uploaded, auto_upload=True, max_files=1) \
            .props(f'accept="{accept}" flat bordered dense label="Or from this device"').classes("w-full")

    async def _file_from_pc(self, kind: str, put: Callable[[EntryTable, str], Any]) -> None:
        endings = tuple(ending for ending, mime in ENDINGS.items() if mime.startswith(f"{kind}/"))
        found = await self._pick_file(endings)
        if found:
            self._use_file(*found, put)

    def _use_file(self, file_name: str, content: bytes, put: Callable[[EntryTable, str], Any]) -> None:
        stored = self._take_file(file_name, content)
        if stored:
            self._edit("file", lambda t: put(t, stored))

    # changes

    def _edit(self, key: str, what: Callable[[EntryTable], Any], whole: bool = True) -> None:
        """Changes the table (what(table)) through the editor's undo; whole: the table and the cell's settings
        are drawn again too (a value being typed keeps its focus)."""
        def apply(design: ElementDesign) -> None:
            self._design = design  # the editor's design (after an undo it is another object)
            table = design.list_entry(self._layer, self._name, self._event)
            what(table)
            design.set_list_entry(self._layer, self._name, self._event, table)
        self._change(f"{self._layer}/{self._name}/entry/{self._event}/{key}", apply, group=not whole)
        self._grid.refresh()
        if whole:
            self._cell_panel.refresh()
            self._layers_panel.refresh()
        self._preview()
        if "address" in key:  # a path on this PC: the toolbox gives it once the editor saved it
            ui.timer(1.5, self._preview, once=True)

    def _preview(self) -> None:
        table = self._table().data
        sample = {**DesignValues.list_sample(self._values), **SAMPLES.get(self._event, {})}
        for cell in table["cells"]:
            if cell.get("emoji_dict") and not isinstance(sample.get(cell["emoji_dict"]), dict):
                sample[cell["emoji_dict"]] = SAMPLE_EMOJI
        media = self._media("")  # /overlay/widget/<name>/media/
        local = media.rsplit("/media/", 1)[0] + "/local?path="
        ui.run_javascript(
            "(() => { const box = document.getElementById(%s); if (!box || !window.TOOLBOX_ENTRY) return; "
            "box.replaceChildren(TOOLBOX_ENTRY.draw(%s, %s, {media: f => %s + encodeURIComponent(f), local: %s}));"
            " })()"
            % (json.dumps(self._preview_id), json.dumps(table, ensure_ascii=False),
               json.dumps(sample, ensure_ascii=False), json.dumps(media), json.dumps(local)))
