from copy import deepcopy
from typing import Any
from urllib.parse import quote

from nicegui import ui

from streamer_toolbox.core.actions.action_description import required_and_optional_params
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.deck.deck import Deck
from streamer_toolbox.core.deck.deck_button import DeckButton
from streamer_toolbox.core.deck.deck_images import DeckImages
from streamer_toolbox.core.deck.deck_page import MOST, DeckPage
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.gui.components.live_deck.deck_button_dialog import DELETE, DeckButtonDialog
from streamer_toolbox.gui.services.activity_log import ActivityLog

HEAD = '<link rel="stylesheet" href="/static/live_deck.css"><script src="/static/live_deck.js"></script>'
MOVED = "tb_deck_spot"  # live_deck.js: a button was dragged to another spot or size
CELL_AT_LEAST = 64  # px: a cell is never smaller (a phone scrolls the page sideways)


class LiveDeckView:
    """The Live deck in one browser tab: pages as tabs, each a grid of cells with the buttons (colour, icon or
    picture, label, text colour) where he put them, in the size he gave them (his wish of 2026-10-13: "like a
    sammi view, where I can set the buttons how I want"). A press runs the button's action and the button
    pulses until it's done (a looping flow keeps pulsing). The pencil switches to editing: drag a button to
    move it, drag its corner to change its size, click it to change what it is; the row above adds a button,
    sets the page's columns, rows and background and adds / renames / moves / deletes pages. Every change is
    saved at once; other open Live pages pick it up within two seconds."""

    def __init__(self, store: DeckStore, actions: ActionRegistry, flows: FlowLibrary, activity: ActivityLog,
                 images: DeckImages) -> None:
        self._store = store
        self._actions = actions
        self._flows = flows
        self._activity = activity
        self._images = images
        self._deck: Deck = store.load()
        self._page = self._deck.pages[0].name if self._deck.pages else ""
        self._editing = False
        self._seen = store.version
        self._running: dict[int, int] = {}  # id() of a button → how many of its presses still run (this tab)

    def build(self) -> None:
        ui.add_head_html(HEAD)
        ui.on(MOVED, lambda e: self._placed(e.args))
        self._view()
        ui.timer(2.0, self._check_saved_elsewhere)

    def _check_saved_elsewhere(self) -> None:
        if self._store.version != self._seen and not self._editing:
            self._seen = self._store.version
            self._deck = self._store.load()
            if not self._deck.page(self._page):
                self._page = self._deck.pages[0].name if self._deck.pages else ""
            self._view.refresh()

    @ui.refreshable_method
    def _view(self) -> None:
        with ui.row().classes("w-full items-center no-wrap gap-2"):
            with ui.tabs(value=self._page or None, on_change=lambda e: self._show_page(e.value)) \
                    .props("dense inline-label outside-arrows mobile-arrows no-caps align=left") \
                    .classes("flex-1 min-w-0"):
                for page in self._deck.pages:
                    ui.tab(page.name)
            ui.button(icon="check" if self._editing else "edit", on_click=self._toggle_edit) \
                .props(f"round dense {'unelevated' if self._editing else 'flat'}") \
                .tooltip("Done" if self._editing else "Edit the buttons")
        if self._editing:
            self._page_tools()
        page = self._deck.page(self._page)
        if page is None:
            ui.label("No pages yet: the pencil, then + Page.").classes("opacity-70")
            return
        if not page.buttons and not self._editing:
            ui.label("This page has no buttons yet: the pencil, then Add button.").classes("opacity-70")
            return
        # the cells are squares; while editing their lines show. On a narrow screen a cell keeps a size a
        # thumb can hit and the page is pushed sideways instead
        with ui.element("div").classes("w-full overflow-x-auto"):
            with ui.element("div").classes("tb-deck" + (" tb-deck-edit" if self._editing else "")) \
                    .props(f"data-columns={page.columns} data-rows={page.rows}") \
                    .style(f"aspect-ratio: {page.columns} / {page.rows}; "
                           f"min-width: {page.columns * CELL_AT_LEAST}px; "
                           + (f"background-color: {page.background}; " if page.background else "") +
                           f"background-size: {100 / page.columns:.4f}% {100 / page.rows:.4f}%"):
                for index, button in enumerate(page.buttons):
                    self._tile(page, index, button)

    def _tile(self, page: DeckPage, index: int, button: DeckButton) -> None:
        known = button.action in self._actions
        running = " tb-running" if id(button) in self._running else ""
        tile = ui.element("div").classes("tb-deck-button" + running) \
            .props(f"data-index={index} data-x={button.x} data-y={button.y} data-w={button.w} data-h={button.h}") \
            .style(f"left:{button.x / page.columns * 100:.4f}%; top:{button.y / page.rows * 100:.4f}%; "
                   f"width:{button.w / page.columns * 100:.4f}%; height:{button.h / page.rows * 100:.4f}%")
        tile.on("click", lambda: self._edit(page, index) if self._editing else self._press(button, tile))
        face = f"background-color:{button.color if known else '#757575'}; color:{button.text_color}"
        if button.image and known:
            face += (f"; background-image:url('{DeckImages.url(quote(button.image))}'); "
                     f"background-size:{'cover' if button.fill else 'contain'}")
        with tile:
            with ui.element("div").classes("tb-deck-face" + (" tb-deck-picture" if button.image else "")) \
                    .style(face):
                if not button.image or not known:
                    ui.icon(button.icon if known else "link_off")
                ui.label(button.label).classes("tb-deck-label")
            if self._editing:
                ui.element("div").classes("tb-deck-grip")
                with ui.context_menu():  # his "go" of 2026-10-14
                    ui.menu_item("Change", on_click=lambda: self._edit(page, index)).props("dense")
                    ui.menu_item("Copy", on_click=lambda: self._copy(page, index)).props("dense")
                    ui.menu_item("Delete", on_click=lambda: self._delete(page, index)).props("dense") \
                        .classes("text-negative")
        if not known:
            tile.tooltip(f"{button.action} isn't there anymore (renamed or deleted?): edit it")

    def _placed(self, spot: dict[str, Any]) -> None:
        """A button was dragged to another spot or size (live_deck.js)."""
        page = self._deck.page(self._page)
        if not self._editing or page is None or not 0 <= int(spot["index"]) < len(page.buttons):
            return
        page.put(int(spot["index"]), int(spot["x"]), int(spot["y"]), int(spot["w"]), int(spot["h"]))
        page.buttons.append(page.buttons.pop(int(spot["index"])))  # the last one is drawn on top
        self._save()

    # ---- pressing ----

    async def _press(self, button: DeckButton, tile: ui.element) -> None:
        if button.action not in self._actions:
            ui.notify(f"{button.label}: {button.action} isn't there anymore", type="warning")
            return
        action = self._actions.get(button.action)
        params: dict[str, Any] = dict(button.params)
        missing = [p["name"] for p in required_and_optional_params(action)
                   if p["required"] and p["name"] not in params]
        if missing:
            asked = await self._ask(button.label, missing)
            if asked is None:
                return
            params |= asked
        key = id(button)
        self._running[key] = self._running.get(key, 0) + 1
        tile.classes(add="tb-running")
        try:
            result = await self._actions.run(button.action, **params)
        except Exception as e:
            self._activity.add("Live", button.action, False, e)
            ui.notify(f"{button.label} failed: {e}", type="negative")
            return
        finally:
            self._running[key] -= 1
            if not self._running[key]:  # pressed twice: only the last run ending stops the pulse
                del self._running[key]
                if not tile.is_deleted:
                    tile.classes(remove="tb-running")
        self._activity.add("Live", button.action, True, result)

    @staticmethod
    async def _ask(title: str, names: list[str]) -> dict[str, Any] | None:
        with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full"):
            ui.label(title).classes("text-lg font-semibold")
            fields = {n: ui.input(n.replace("_", " ").capitalize()).props("autofocus" if i == 0 else "")
                      .classes("w-full") for i, n in enumerate(names)}

            def submit() -> None:
                dialog.submit({n: f.value for n, f in fields.items()})

            for field in fields.values():
                field.on("keydown.enter", submit)
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Run", on_click=submit).props("no-caps unelevated")
        result = await dialog
        if not dialog.is_deleted:
            dialog.delete()
        return result

    # ---- editing ----

    def _show_page(self, name: str) -> None:
        if name and name != self._page:
            self._page = name
            self._view.refresh()

    def _toggle_edit(self) -> None:
        self._editing = not self._editing
        self._view.refresh()

    def _save(self) -> None:
        self._store.save(self._deck)
        self._seen = self._store.version
        self._view.refresh()

    async def _edit(self, page: DeckPage, index: int | None) -> None:
        button = page.buttons[index] if index is not None else None
        result = await DeckButtonDialog(button, page.name, [p.name for p in self._deck.pages], self._actions,
                                        self._flows, self._images).open()
        if result is None:
            return
        if index is not None:
            page.buttons.pop(index)
        if result != DELETE:
            edited, target_name = result
            target = self._deck.page(target_name) or page
            if target is page and index is not None:
                page.buttons.insert(index, edited)
            else:  # new, or moved to another page: the first free spot there
                edited.x = edited.y = -1
                target.buttons.append(edited)
                target.place()
        self._save()

    def _copy(self, page: DeckPage, index: int) -> None:
        """A copy of the button on the same page, at the first free spot."""
        copy = deepcopy(page.buttons[index])
        copy.x = copy.y = -1
        page.buttons.append(copy)
        page.place()
        self._save()

    async def _delete(self, page: DeckPage, index: int) -> None:
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete the button {page.buttons[index].label}?")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Delete", icon="delete", on_click=lambda: dialog.submit(True)) \
                    .props("unelevated no-caps color=negative")
        if await dialog:
            page.buttons.pop(index)
            self._save()

    def _set_grid(self, page: DeckPage, columns: Any, rows: Any) -> None:
        if columns and rows and (int(columns), int(rows)) != (page.columns, page.rows):
            page.set_grid(int(columns), int(rows))
            self._save()

    def _set_background(self, page: DeckPage, color: str | None) -> None:
        color = (color or "").strip()
        if color != page.background and (not color or color.startswith("#")):
            page.background = color
            self._save()

    def _page_tools(self) -> None:
        page = self._deck.page(self._page)
        with ui.row().classes("gap-1 items-center"):
            if page:
                ui.button("Add button", icon="add", on_click=lambda: self._edit(page, None)) \
                    .props("unelevated dense no-caps").classes("px-2")
                columns = ui.number("Columns", value=page.columns, min=1, max=MOST, precision=0) \
                    .props("outlined dense").classes("w-24")
                rows = ui.number("Rows", value=page.rows, min=1, max=MOST, precision=0) \
                    .props("outlined dense").classes("w-24")
                for field in (columns, rows):
                    field.on("change", lambda: self._set_grid(page, columns.value, rows.value))
                ui.color_input("Background", value=page.background,
                               on_change=lambda e: self._set_background(page, e.value)) \
                    .props("outlined dense clearable debounce=600").classes("w-36") \
                    .tooltip("Behind the buttons of this page. Empty = the toolbox's own")
                ui.separator().props("vertical").classes("mx-1")
            ui.button("Page", icon="add", on_click=self._add_page).props("flat dense no-caps")
            if page:
                ui.button("Rename", icon="edit", on_click=lambda: self._rename_page(page)).props("flat dense no-caps")
                ui.button(icon="chevron_left", on_click=lambda: self._move_page(page, -1)) \
                    .props("flat round dense").tooltip("Move this page left")
                ui.button(icon="chevron_right", on_click=lambda: self._move_page(page, 1)) \
                    .props("flat round dense").tooltip("Move this page right")
                ui.button("Delete page", icon="delete", on_click=lambda: self._delete_page(page)) \
                    .props("flat dense no-caps color=negative")
            ui.label("Drag a button to move it, its corner to change its size; click it to change it") \
                .classes("text-xs opacity-60 pl-2")

    async def _add_page(self) -> None:
        name = await self._ask_name("New page", self._deck.free_page_name())
        if name:
            name = self._deck.free_page_name(name)
            self._deck.pages.append(DeckPage(name))
            self._page = name
            self._save()

    async def _rename_page(self, page: DeckPage) -> None:
        name = await self._ask_name("Rename page", page.name)
        if name and name != page.name:
            page.name = self._deck.free_page_name(name)
            self._page = page.name
            self._save()

    def _move_page(self, page: DeckPage, by: int) -> None:
        pages = self._deck.pages
        index = pages.index(page)
        target = max(0, min(len(pages) - 1, index + by))
        pages.insert(target, pages.pop(index))
        self._save()

    async def _delete_page(self, page: DeckPage) -> None:
        if page.buttons:
            with ui.dialog() as dialog, ui.card():
                ui.label(f"Delete page {page.name} and its {len(page.buttons)} buttons?")
                with ui.row().classes("w-full justify-end"):
                    ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                    ui.button("Delete", on_click=lambda: dialog.submit(True)).props("unelevated no-caps color=negative")
            sure = await dialog
            dialog.delete()
            if not sure:
                return
        self._deck.pages.remove(page)
        self._page = self._deck.pages[0].name if self._deck.pages else ""
        self._save()

    @staticmethod
    async def _ask_name(title: str, value: str) -> str:
        with ui.dialog() as dialog, ui.card().classes("w-80"):
            ui.label(title).classes("font-semibold")
            name = ui.input("Name", value=value).props("outlined dense autofocus").classes("w-full")
            name.on("keydown.enter", lambda: dialog.submit(name.value))
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit("")).props("flat no-caps")
                ui.button("OK", on_click=lambda: dialog.submit(name.value)).props("unelevated no-caps")
        result = await dialog
        dialog.delete()
        return (result or "").strip()
