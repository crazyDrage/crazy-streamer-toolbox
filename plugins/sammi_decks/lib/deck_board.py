from typing import Any
from urllib.parse import quote

from nicegui import ui

from streamer_toolbox.core.interfaces.plugin_context import PluginContext

from .deck_filter import Deck, DeckFilter
from .deck_layouts import DeckLayouts, Layout

GET_DECKS, PRESS, SET_DECK = "sammi.get_decks", "sammi.trigger_button", "sammi.set_deck"
GET_VARIABLE, FOLDER_VARIABLE = "sammi.get_variable", "main_directory"  # SAMMI says where it is installed
VIEWS = {"grid": "Grid", "list": "List"}
SHAPES = {"16 / 10": "16:10 (tablet)", "16 / 9": "16:9", "4 / 3": "4:3", "3 / 4": "3:4 (phone upright)"}
PAGE_BUTTONS = {"<-": -1, "->": 1}  # Deck Hopper's page buttons: in the grid they flip to the deck before / after
GRID_CSS = """<style>
.tb-sammi-deck { position: relative; width: 100%; border-radius: 10px; overflow: hidden; container-type: inline-size; }
.tb-sammi-button { position: absolute; display: flex; align-items: center; justify-content: center; padding: 2px;
  text-align: center; white-space: pre-line; line-height: 1.1; cursor: pointer; user-select: none; overflow: hidden;
  font-size: clamp(9px, 1.7cqw, 24px); font-weight: 600; border-radius: 4px; background-position: center;
  background-repeat: no-repeat; transition: transform 0.06s, filter 0.06s; word-break: break-word; }
.tb-sammi-button:active { transform: scale(0.95); filter: brightness(1.25); }
.tb-sammi-shadow { text-shadow: 0 1px 2px #000, 0 0 3px #000; }
</style>"""


class DeckBoard:
    """The tool: SAMMI's decks as chips on top, the picked deck's buttons below. A tap presses the button in SAMMI.
    Grid: the buttons where SAMMI (and Deck Hopper) put them, with their colours and pictures, read from SAMMI's
    deck file (SAMMI is asked for its folder, or it is set in Settings); <- and -> flip to the deck before / after.
    List: every button in a simple grid, also for a deck without a layout. The search box finds a button in every
    deck. Settings (gear): SAMMI folder, deck shape, decks and button texts to hide, button size; kept with
    ctx.save_settings. Reads SAMMI fresh each time the tool opens or ↻ is pressed."""

    def __init__(self, ctx: PluginContext, layouts: DeckLayouts, images: dict[str, str]) -> None:
        self._ctx = ctx
        self._layouts = layouts
        self._images = images
        self._asked_folder = ""  # SAMMI's own answer, used while the setting is empty
        self._decks: list[Deck] = []
        self._error = ""
        self._search = ""

    def build(self) -> None:
        with ui.row().classes("items-center w-full gap-2"):
            ui.image(self._ctx.resource_url("deck.svg")).classes("w-7 h-7")
            ui.input(placeholder="find a button in all decks", on_change=lambda e: self._find(e.value)) \
                .props("dense outlined clearable debounce=250").classes("flex-1 min-w-[12rem]")
            ui.toggle(VIEWS, value=self._ctx.settings().get("view", "grid"),
                      on_change=lambda e: self._set_view(e.value)).props("no-caps dense")
            ui.button(icon="refresh", on_click=self._reload).props("flat round").tooltip("Read SAMMI again")
            ui.button(icon="settings", on_click=self._settings_dialog).props("flat round").tooltip("Settings")
        ui.add_head_html(GRID_CSS)
        self._board()
        ui.timer(0.05, self._reload, once=True)

    def _set_view(self, view: str) -> None:
        self._ctx.save_settings({"view": view})
        self._board.refresh()

    async def _reload(self) -> None:
        if not self._ctx.has_action(GET_DECKS):
            self._decks, self._error = [], "The SAMMI connection isn't loaded."
        else:
            try:
                self._decks, self._error = list(await self._ctx.run_action(GET_DECKS)), ""
            except Exception as e:  # SAMMI closed, switched off, ...
                self._decks, self._error = [], f"Can't read SAMMI: {e}"
        if not self._error and not self._ctx.settings().get("sammi_folder") and self._ctx.has_action(GET_VARIABLE):
            try:
                self._asked_folder = str(await self._ctx.run_action(GET_VARIABLE, name=FOLDER_VARIABLE) or "")
            except Exception:  # an older SAMMI without the variable: the folder stays a setting
                self._asked_folder = ""
        self._board.refresh()

    def _folder(self, settings: dict[str, Any]) -> str:
        return settings.get("sammi_folder", "") or self._asked_folder

    def _find(self, words: str | None) -> None:
        self._search = (words or "").strip()
        self._board.refresh()

    @ui.refreshable_method
    def _board(self) -> None:
        settings = self._ctx.settings()
        filters = DeckFilter(settings.get("hide_texts", []), settings.get("hide_decks", []))
        if self._error:
            ui.label(self._error + " See Connections → SAMMI.").classes("text-warning")
            return
        decks = filters.decks(self._decks)
        if not decks:
            ui.label("Reading SAMMI..." if not self._decks else "Every deck is hidden (Settings).") \
                .classes("opacity-70")
            return
        if self._search:
            found = filters.search(decks, self._search)
            ui.label(f"{len(found)} found").classes("text-sm opacity-70")
            self._grid([(b, deck["name"]) for deck, b in found], settings)
            return
        names = [d["name"] for d in decks]
        current = settings.get("last_deck") if settings.get("last_deck") in names else names[0]
        deck = next(d for d in decks if d["name"] == current)
        with ui.row().classes("w-full gap-1"):
            for d in decks:
                ui.chip(d["name"], icon="check_circle" if d["enabled"] else "radio_button_unchecked",
                        color="primary" if d["name"] == current else None,
                        on_click=lambda n=d["name"]: self._pick(n)) \
                    .props("clickable" + ("" if d["name"] == current else " outline")) \
                    .tooltip("on in SAMMI" if d["enabled"] else "off in SAMMI")
        with ui.row().classes("items-center gap-2"):
            ui.label(deck["name"]).classes("text-lg font-semibold")
            ui.switch("on in SAMMI", value=bool(deck["enabled"]),
                      on_change=lambda e, d=deck: self._set_deck(d, e.value))
        layout = self._layouts.layouts(self._folder(settings)).get(deck["id"]) \
            if settings.get("view", "grid") == "grid" else None
        if layout:
            self._deck_grid(deck, layout, settings, names)
            return
        if settings.get("view", "grid") == "grid":
            ui.label("No layout for this deck (SAMMI's folder wasn't found: set it in Settings; an encrypted deck has none): "
                     "shown as a list.").classes("text-xs opacity-60")
        self._grid([(b, "") for b in filters.buttons(deck)], settings)

    def _deck_grid(self, deck: Deck, layout: Layout, settings: dict[str, Any], names: list[str]) -> None:
        """The deck as SAMMI lays it out: each button at its spot and size, in its colours, with its picture."""
        images = self._image_url(self._folder(settings))
        shape = settings.get("deck_shape", "16 / 10")
        with ui.element("div").classes("tb-sammi-deck") \
                .style(f"aspect-ratio: {shape}; background: {layout['background']}"):
            for button in deck.get("buttons", []):
                spot = layout["buttons"].get(button["id"])
                if spot is None:
                    continue
                text = str(button.get("text", "")).strip()
                style = (f"left:{spot['x'] * 100:.3f}%; top:{spot['y'] * 100:.3f}%; width:{spot['w'] * 100:.3f}%; "
                         f"height:{spot['h'] * 100:.3f}%; color:{spot['font_color']}; "
                         f"background-color:{'transparent' if spot['transparent'] else spot['color']}; "
                         f"border:{spot['border']:.0f}px solid {spot['border_color']};")
                if spot["image"] and images:
                    size = "100% 100%" if spot["stretch"] else "contain"
                    style += f" background-image:url('{images}/{quote(spot['image'])}'); background-size:{size};"
                page = PAGE_BUTTONS.get(text)
                tile = ui.element("div").classes("tb-sammi-button tb-sammi-shadow").style(style)
                if page:
                    tile.on("click", lambda by=page: self._flip(names, by))
                    tile.tooltip("deck before" if page < 0 else "deck after")
                else:
                    tile.on("click", lambda b=button: self._press(b))
                    tile.tooltip(f"ID {button['id']}")
                with tile:
                    ui.label(text)

    def _image_url(self, sammi_folder: str) -> str:
        """SAMMI's picture folder as a URL, served the first time it's needed."""
        folder = self._layouts.images(sammi_folder)
        if folder is None:
            return ""
        if str(folder) not in self._images:
            self._images[str(folder)] = self._ctx.add_static(folder)
        return self._images[str(folder)]

    def _flip(self, names: list[str], by: int) -> None:
        current = self._ctx.settings().get("last_deck")
        index = names.index(current) if current in names else 0
        self._pick(names[(index + by) % len(names)])

    def _grid(self, buttons: list[tuple[dict[str, Any], str]], settings: dict[str, Any]) -> None:
        size = int(settings.get("button_size", 130))
        with ui.element("div").classes("w-full gap-2").style(
                f"display:grid; grid-template-columns:repeat(auto-fill, minmax({size}px, 1fr))"):
            for button, deck_name in buttons:
                text = str(button.get("text", "")).strip() or button["id"]
                with ui.button(on_click=lambda b=button: self._press(b)) \
                        .props("no-caps unelevated color=primary").classes("w-full") \
                        .style(f"min-height:{max(size // 2, 48)}px").tooltip(f"ID {button['id']}"):
                    with ui.column().classes("items-center gap-0"):
                        ui.label(text).classes("whitespace-pre-line leading-tight text-center break-all")
                        if deck_name:
                            ui.label(deck_name).classes("text-xs opacity-70")

    async def _press(self, button: dict[str, Any]) -> None:
        label = DeckFilter.text(button) or button["id"]
        try:
            await self._ctx.run_action(PRESS, button_id=button["id"])
        except Exception as e:
            ui.notify(f"{label}: {e}", type="negative", multi_line=True)
            return
        ui.notify(f"Pressed {label}", type="positive", timeout=1200)

    async def _set_deck(self, deck: Deck, on: bool) -> None:
        if bool(deck["enabled"]) == on:
            return
        try:
            await self._ctx.run_action(SET_DECK, deck=deck["id"], state="on" if on else "off")
            deck["enabled"] = on
        except Exception as e:
            ui.notify(f"{deck['name']}: {e}", type="negative")
        self._board.refresh()

    def _pick(self, name: str) -> None:
        self._ctx.save_settings({"last_deck": name})
        self._board.refresh()

    def _settings_dialog(self) -> None:
        settings = self._ctx.settings()
        with ui.dialog() as dialog, ui.card().classes("w-[440px] max-w-[95vw] gap-3"):
            ui.label("SAMMI decks: settings").classes("text-lg font-semibold")
            folder = ui.input("SAMMI folder (where SAMMI Core.exe is)", value=settings.get("sammi_folder", "")) \
                .props("outlined dense").classes("w-full")
            if self._asked_folder:
                folder.props(f'placeholder="{self._asked_folder}"')
            ui.label("For the Grid: the toolbox only reads SAMMI's deck file there, it never changes it. "
                     "Empty = SAMMI is asked where it is") \
                .classes("text-xs opacity-60 -mt-2")
            shape = ui.select(SHAPES, value=settings.get("deck_shape", "16 / 10"), label="deck shape (Grid)") \
                .props("outlined dense").classes("w-full")
            hide_decks = ui.select([d["name"] for d in self._decks], value=settings.get("hide_decks", []),
                                   multiple=True, label="hide these decks").props("use-chips outlined dense") \
                .classes("w-full")
            hide_texts = ui.input("hide buttons with this text (comma between)",
                                  value=", ".join(t or "(empty)" for t in settings.get("hide_texts", []))) \
                .props("outlined dense").classes("w-full")
            size = ui.slider(min=80, max=260, step=10, value=int(settings.get("button_size", 130)))
            ui.label().bind_text_from(size, "value", lambda v: f"button width: {v}px").classes("text-xs")

            def save() -> None:
                texts = [t.strip() for t in (hide_texts.value or "").split(",")]
                self._ctx.save_settings({"sammi_folder": (folder.value or "").strip().strip('"'),
                                         "deck_shape": shape.value,
                                         "hide_decks": list(hide_decks.value or []),
                                         "hide_texts": ["" if t == "(empty)" else t for t in texts if t],
                                         "button_size": int(size.value)})
                dialog.close()
                self._board.refresh()

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
                ui.button("Save", icon="save", on_click=save).props("unelevated no-caps")
        dialog.open()
