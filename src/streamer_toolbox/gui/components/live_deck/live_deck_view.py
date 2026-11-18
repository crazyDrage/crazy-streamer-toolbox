from collections.abc import Callable
from copy import deepcopy
from typing import Any
from urllib.parse import quote

from nicegui import app, ui

from streamer_toolbox.core.actions.action_description import required_and_optional_params
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.deck.deck import Deck
from streamer_toolbox.core.deck.deck_button import GO_TO_PAGE, DeckButton
from streamer_toolbox.core.deck.deck_images import DeckImages
from streamer_toolbox.core.deck.deck_page import MOST, DeckPage
from streamer_toolbox.core.deck.deck_pager import DeckPager
from streamer_toolbox.core.deck.deck_states import DeckStates
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.gui.components.flow_editor.action_picker import ActionPicker
from streamer_toolbox.gui.components.live_deck.deck_button_dialog import DELETE, DeckButtonDialog
from streamer_toolbox.gui.services.activity_log import ActivityLog

HEAD = '<link rel="stylesheet" href="/static/live_deck.css"><script src="/static/live_deck.js"></script>'
MOVED = "tb_deck_spot"  # live_deck.js: a button was dragged to another spot or size
TURNED = "tb_deck_turn"  # live_deck.js: a swipe or an arrow key, {by: 1 or -1}: the next / last page
CELL_AT_LEAST = 64  # px: a cell is never smaller (a phone scrolls the page sideways) when it fits the width
SIZE_KEY = "live_size"  # app.storage.user (this browser): "width", "screen" or a cell's size in px
SIZES = {"width": "Fit the width", "screen": "Fit the screen"}
FIXED_LIMITS = (16, 400)  # px: a fixed cell's size
BUTTONS_ONLY = "/live/buttons"  # the deck on its own (LivePage.build_bare)
EDIT_KEY = "live_editing"  # app.storage.user: editing stays on when another page is picked in the side list
CLIPBOARD_KEY = "live_clipboard"  # app.storage.user: the button Copy kept, to paste on any page
KEYED = "tb_deck_key"  # live_deck.js, editing: Ctrl+C / X / V / Z, Delete, Escape {key, index, x, y} (under the mouse)
START_KEY = "live_start_page"  # app.storage.user: the page this device opens Live with (his 11-18 pick 14)
PICKED = "tb_deck_cell"  # a right-click on the page while editing: {x, y}, the cell under the mouse
# the cell under the mouse, worked out in the browser (the page knows its columns and rows)
PICK_CELL = ("(e) => { const b = e.currentTarget; const r = b.getBoundingClientRect(); emitEvent('tb_deck_cell', "
             "{x: Math.floor((e.clientX - r.left) / r.width * Number(b.dataset.columns)), "
             "y: Math.floor((e.clientY - r.top) / r.height * Number(b.dataset.rows))}); }")
# run in the browser: it only allows full screen from the click itself (no trip to the server first)
FULL_SCREEN = ("() => document.fullscreenElement ? document.exitFullscreen() : "
               "document.documentElement.requestFullscreen().catch((e) => console.warn('full screen:', e))")


class LiveDeckView:
    """The Live deck in one browser tab: pages as tabs, each a grid of cells with the buttons (colour, icon or
    picture, label, text colour) where he put them, in the size he gave them (his wish of 2026-10-13: "like a
    sammi view, where I can set the buttons how I want"). A press runs the button's action and the button
    pulses until it's done (a looping flow keeps pulsing). The pencil switches to editing: drag a button to
    move it, drag its corner to change its size, click it to change what it is; the row above adds a button,
    sets the page's columns, rows and background and adds / renames / moves / deletes pages. Every change is
    saved at once; other open Live pages pick it up within two seconds.

    The view menu (his round 63): the size of the cells (fit the width, fit the screen without scrolling, or a
    fixed size: smaller buttons; kept per browser), Only the buttons (/live/buttons: the page tabs and the
    buttons, nothing of the toolbox around them; `bare`) and Full screen (only the buttons: a swipe or the arrow
    keys go to the next page, the corner button or Esc leave it; for a tablet). In full screen a small lip on the
    left opens the list of pages. A button can also go to another page (GO_TO_PAGE), like his SAMMI buttons.

    His 11-18 picks (temp/research/20_live_deck_ideas.md): Cut / Move to page / Swap places in the button's menu;
    keys while editing (Ctrl+C / X / V / Z under the mouse, Delete, Escape; Page Up / Down turn the page); Undo
    (DeckStore keeps the last saves); a button may ask first (confirm); a start page per device (view menu);
    a flow can turn the page (DeckPager, box Show Live page); a button with a state shows its on look while
    the output of its flow it follows means on (DeckStates)."""

    def __init__(self, store: DeckStore, states: DeckStates, pager: DeckPager, actions: ActionRegistry,
                 flows: FlowLibrary, activity: ActivityLog, images: DeckImages, picker: Callable[[], ActionPicker],
                 bare: bool = False) -> None:
        self._store = store
        self._states = states
        self._pager = pager
        self._states_seen = states.version
        self._pager_seen = pager.version
        self._swapping: int | None = None  # Swap places: the button that waits for the one to swap with
        self._actions = actions
        self._picker = picker
        self._flows = flows
        self._activity = activity
        self._images = images
        self._deck: Deck = store.load()
        self._page = self._deck.pages[0].name if self._deck.pages else ""
        self._editing = False
        self._seen = store.version
        self._running: dict[int, int] = {}  # id() of a button → how many of its presses still run (this tab)
        self._spot: tuple[int, int] | None = None  # the cell last right-clicked while editing
        self._bare = bare

    def build(self) -> None:
        self._user = app.storage.user  # this browser's; only reachable while the page is built
        # /?show=<page> (the side list) picks the page; &edit=1 keeps editing after a page was added, renamed,
        # moved or deleted (the page loads again so the side list shows it)
        params = ui.context.client.request.query_params
        if self._deck.page(params.get("show", "")):
            self._page = params["show"]
        elif self._deck.page(self._user.get(START_KEY, "")):
            self._page = self._user[START_KEY]
        self._editing = not self._bare and (params.get("edit") == "1" or bool(self._user.get(EDIT_KEY)))
        ui.add_head_html(HEAD)
        ui.on(MOVED, lambda e: self._placed(e.args))
        ui.on(TURNED, lambda e: self._turn(int(e.args.get("by", 1))))
        ui.on(PICKED, lambda e: self._picked(e.args))
        ui.on(KEYED, lambda e: self._key(e.args))
        ui.button(icon="fullscreen_exit").props("flat round dense").classes("tb-deck-exit") \
            .on("click", js_handler=FULL_SCREEN)
        self._view()
        ui.timer(1.0, self._check_elsewhere)

    def _check_elsewhere(self) -> None:
        """Not while editing: a save on another device, a flow's new output (a button's state), a flow turning
        the page."""
        if self._editing:
            return
        changed = False
        if self._store.version != self._seen:
            self._seen = self._store.version
            self._deck = self._store.load()
            if not self._deck.page(self._page):
                self._page = self._deck.pages[0].name if self._deck.pages else ""
            changed = True
        if self._pager.version != self._pager_seen:
            self._pager_seen = self._pager.version
            if self._deck.page(self._pager.page) and self._pager.page != self._page:
                self._page = self._pager.page
                changed = True
        if self._states.version != self._states_seen:
            self._states_seen = self._states.version
            changed = True
        if changed:
            self._view.refresh()

    @ui.refreshable_method
    def _view(self) -> None:
        # the pages: in the toolbox they are the side list (like Flows); on their own, and while editing (his
        # 11-17: "you can't change page in the edit view"), every page is a button here too (they wrap onto
        # more lines instead of scrolling away), the one shown is filled
        with ui.row().classes("tb-deck-bar w-full items-start no-wrap gap-2"):
            with ui.row().classes("flex-1 min-w-0 gap-1"):
                for page in self._deck.pages if self._bare or self._editing else []:
                    here = page.name == self._page
                    ui.button(page.name, on_click=lambda n=page.name: self._show_page(n)) \
                        .props(f"no-caps dense {'unelevated color=primary' if here else 'flat'}") \
                        .classes("px-3")
            self._view_menu()
            if not self._bare:
                ui.button(icon="check" if self._editing else "edit", on_click=self._toggle_edit) \
                    .props(f"round dense {'unelevated' if self._editing else 'flat'}") \
                    .tooltip("Done" if self._editing else "Edit the buttons")
        # full screen only (live_deck.css): the lip on the left opens the pages; picking one closes it (the
        # refresh draws it closed)
        ui.button(icon="chevron_right").props("flat dense").classes("tb-deck-lip") \
            .on("click", js_handler="() => document.querySelector('.tb-deck-drawer').classList.toggle('open')")
        with ui.element("div").classes("tb-deck-drawer"):
            for page in self._deck.pages:
                ui.button(page.name, on_click=lambda n=page.name: self._show_page(n)) \
                    .props(f"no-caps align=left {'unelevated color=primary' if page.name == self._page else 'flat'}") \
                    .classes("w-full")
        if self._editing:
            self._page_tools()
        page = self._deck.page(self._page)
        if page is None:
            ui.label("No pages yet: the pencil, then + Page.").classes("opacity-70")
            return
        if not page.buttons and not self._editing:
            ui.label("This page has no buttons yet: the pencil, then Add button.").classes("opacity-70")
            return
        # the cells are squares; while editing their lines show. Fit the width: on a narrow screen a cell keeps a
        # size a thumb can hit and the page is pushed sideways instead. Fit the screen: live_deck.js keeps it as
        # high as the window. Fixed: every cell that many px
        size = self._size()
        width = (f"width: {page.columns * size}px; " if isinstance(size, int) else
                 f"min-width: {page.columns * CELL_AT_LEAST}px; " if size == "width" else "")
        # "safe center": a deck wider than the screen starts at the left edge and scrolls, instead of being
        # centred with its left part out of reach (seen on a phone, 11-18)
        with ui.element("div").classes("w-full overflow-auto flex").style("justify-content: safe center"):
            with ui.element("div").classes("tb-deck" + (" tb-deck-edit" if self._editing else "")) \
                    .props(f"data-columns={page.columns} data-rows={page.rows}"
                           + (" data-fit=screen" if size == "screen" else "")) \
                    .style(f"aspect-ratio: {page.columns} / {page.rows}; flex: none; {width}"
                           + ("" if isinstance(size, int) else "width: 100%; ")
                           + (f"background-color: {page.background}; " if page.background else "") +
                           f"background-size: {100 / page.columns:.4f}% {100 / page.rows:.4f}%"):
                for index, button in enumerate(page.buttons):
                    self._tile(page, index, button)
                if not self._bare:
                    self._board_menu(page)

    def _tile(self, page: DeckPage, index: int, button: DeckButton) -> None:
        known = (self._deck.page(button.params.get("page", "")) is not None if button.action == GO_TO_PAGE
                 else button.action in self._actions)
        running = " tb-running" if id(button) in self._running else ""
        tile = ui.element("div").classes("tb-deck-button" + running) \
            .props(f"data-index={index} data-x={button.x} data-y={button.y} data-w={button.w} data-h={button.h}") \
            .style(f"left:{button.x / page.columns * 100:.4f}%; top:{button.y / page.rows * 100:.4f}%; "
                   f"width:{button.w / page.columns * 100:.4f}%; height:{button.h / page.rows * 100:.4f}%")
        tile.on("click", lambda: self._clicked(page, index, button, tile))
        on = known and self._states.is_on(button)
        if on:
            tile.classes(add="tb-deck-on")
        color = (button.on_color or button.color) if on else button.color
        text_color = (button.on_text_color or button.text_color) if on else button.text_color
        icon = (button.on_icon or button.icon) if on else button.icon
        label = (button.on_label or button.label) if on else button.label
        if self._swapping == index:
            tile.classes(add="tb-deck-swapping")
        face = f"background-color:{color if known else '#757575'}; color:{text_color}"
        if button.image and known:
            face += (f"; background-image:url('{DeckImages.url(quote(button.image))}'); "
                     f"background-size:{'cover' if button.fill else 'contain'}")
        with tile:
            with ui.element("div").classes("tb-deck-face" + (" tb-deck-picture" if button.image else "")) \
                    .style(face):
                if not button.image or not known:
                    ui.icon(icon if known else "link_off")
                ui.label(label).classes("tb-deck-label")
            if self._editing:
                ui.element("div").classes("tb-deck-grip")
            if not self._bare:  # the menu also outside editing (his 11-18: "at least an edit option")
                tile.on("contextmenu", js_handler="(e) => e.stopPropagation()")  # not the page's menu too
                with ui.context_menu():  # his "go" of 2026-10-14
                    self._edit_switch_item()
                    ui.menu_item("Change", on_click=lambda: self._edit(page, index)).props("dense")
                    ui.menu_item("Copy", on_click=lambda: self._copy(page, index)).props("dense") \
                        .tooltip("Keep it to paste on any page: right-click a free spot, Paste button here")
                    ui.menu_item("Cut", on_click=lambda: self._cut(page, index)).props("dense") \
                        .tooltip("Copy, then take it off this page")
                    ui.menu_item("Duplicate", on_click=lambda: self._duplicate(page, index)).props("dense")
                    if len(self._deck.pages) > 1:
                        ui.menu_item("Move to page ...", on_click=lambda: self._move_to_page(page, index)) \
                            .props("dense")
                    if len(page.buttons) > 1:
                        ui.menu_item("Swap places ...", on_click=lambda: self._start_swap(index)).props("dense") \
                            .tooltip("Then click the button it swaps places with")
                    ui.menu_item("Delete", on_click=lambda: self._delete(page, index)).props("dense") \
                        .classes("text-negative")
        if not known:
            gone = f"page {button.params.get('page', '')}" if button.action == GO_TO_PAGE else button.action
            tile.tooltip(f"{gone} isn't there anymore (renamed or deleted?): edit it")

    # ---- the view ----

    def _size(self) -> str | int:
        size = self._user.get(SIZE_KEY, "screen" if self._bare else "width")
        return size if size in SIZES or isinstance(size, int) else "width"

    def _view_menu(self) -> None:
        size = self._size()
        with ui.button(icon="aspect_ratio").props("flat round dense").tooltip("View: size, only the buttons, "
                                                                              "full screen"):
            with ui.menu():
                for key, text in SIZES.items():
                    ui.menu_item(("✓ " if size == key else "") + text, on_click=lambda k=key: self._set_size(k))
                ui.menu_item((f"✓ Fixed: {size} px per cell" if isinstance(size, int) else "Fixed size ...")
                             , on_click=self._ask_size)
                ui.separator()
                if self._page:
                    start = self._user.get(START_KEY) == self._page
                    ui.menu_item(("✓ " if start else "") + "Start with this page on this device",
                                 on_click=self._toggle_start_page)
                    ui.separator()
                if self._bare:
                    ui.menu_item("Back to the toolbox", on_click=lambda: ui.navigate.to("/"))
                else:
                    ui.menu_item("Only the buttons", on_click=lambda: ui.navigate.to(BUTTONS_ONLY))
                ui.menu_item("Full screen (only the buttons)").on("click", js_handler=FULL_SCREEN)

    def _set_size(self, size: str | int) -> None:
        self._user[SIZE_KEY] = size
        self._view.refresh()

    async def _ask_size(self) -> None:
        low, high = FIXED_LIMITS
        size = self._size()
        with ui.dialog() as dialog, ui.card().classes("w-80"):
            ui.label("Size of a cell").classes("font-semibold")
            ui.label("A button one cell big is this many pixels wide and high; smaller = smaller buttons. "
                     "Kept for this browser.").classes("text-xs opacity-70")
            field = ui.number("px", value=size if isinstance(size, int) else 64, min=low, max=high, precision=0) \
                .props("outlined dense autofocus").classes("w-full")
            ui.slider(min=low, max=high, step=4).bind_value(field)
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("OK", on_click=lambda: dialog.submit(field.value)).props("unelevated no-caps")
        result = await dialog
        dialog.delete()
        if result:
            self._set_size(max(low, min(high, int(result))))

    def _toggle_start_page(self) -> None:
        if self._user.get(START_KEY) == self._page:
            self._user.pop(START_KEY, None)
            ui.notify("This device opens Live with the first page again")
        else:
            self._user[START_KEY] = self._page
            ui.notify(f"This device opens Live with {self._page}")
        self._view.refresh()

    def _turn(self, by: int) -> None:
        """A swipe, an arrow key or Page Up / Down: the next page (by 1) or the one before (-1), round the end.
        (live_deck.js sends no swipes or arrows while editing; Page Up / Down also work then.)"""
        names = [p.name for p in self._deck.pages]
        if len(names) < 2:
            return
        index = names.index(self._page) if self._page in names else 0
        self._show_page(names[(index + by) % len(names)])

    def _placed(self, spot: dict[str, Any]) -> None:
        """A button was dragged to another spot or size (live_deck.js)."""
        page = self._deck.page(self._page)
        if not self._editing or page is None or not 0 <= int(spot["index"]) < len(page.buttons):
            return
        page.put(int(spot["index"]), int(spot["x"]), int(spot["y"]), int(spot["w"]), int(spot["h"]))
        page.buttons.append(page.buttons.pop(int(spot["index"])))  # the last one is drawn on top
        self._save()

    # ---- pressing ----

    async def _clicked(self, page: DeckPage, index: int, button: DeckButton, tile: ui.element) -> None:
        if self._swapping is not None:
            self._swap_with(page, index)
        elif self._editing:
            await self._edit(page, index)
        else:
            await self._press(button, tile)

    async def _press(self, button: DeckButton, tile: ui.element) -> None:
        if button.confirm and not await self._sure(f"Run {button.label}?", "Run"):
            return
        if button.action == GO_TO_PAGE:
            if not self._deck.page(button.params.get("page", "")):
                ui.notify(f"{button.label}: page {button.params.get('page', '')} isn't there anymore", type="warning")
                return
            self._show_page(button.params["page"])
            return
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
    async def _sure(question: str, yes: str, danger: bool = False) -> bool:
        with ui.dialog() as dialog, ui.card():
            ui.label(question)
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button(yes, on_click=lambda: dialog.submit(True)) \
                    .props("unelevated no-caps" + (" color=negative" if danger else "")) \
                    .classes("tb-deck-sure")
        result = await dialog
        if not dialog.is_deleted:
            dialog.delete()
        return bool(result)

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
        self._user[EDIT_KEY] = self._editing  # picking a page in the side list loads Live again
        self._view.refresh()

    @staticmethod
    def address(page: str) -> str:
        """The Live page showing this deck page."""
        return f"/?show={quote(page, safe='')}"

    def _pages_changed(self) -> None:
        """A page was added, renamed, moved or deleted: saved, and in the toolbox the page loads again so the
        side list has it."""
        if self._bare:
            self._save()
            return
        self._store.save(self._deck)
        self._seen = self._store.version
        ui.navigate.to(self.address(self._page) + "&edit=1")

    def _save(self) -> None:
        self._store.save(self._deck)
        self._seen = self._store.version
        self._view.refresh()

    async def _edit(self, page: DeckPage, index: int | None, spot: tuple[int, int] | None = None) -> None:
        button = page.buttons[index] if index is not None else None
        result = await DeckButtonDialog(button, page.name, [p.name for p in self._deck.pages], self._actions,
                                        self._flows, self._images, self._picker).open()
        if result is None:
            return
        if index is not None:
            page.buttons.pop(index)
        if result != DELETE:
            edited, target_name = result
            target = self._deck.page(target_name) or page
            if target is page and index is not None:
                page.buttons.insert(index, edited)
            else:  # new (at the right-clicked cell, if any), or moved to another page: the first free spot there
                self._add(target, edited, spot if target is page else None)
        self._save()

    def _board_menu(self, page: DeckPage) -> None:
        """Right-click on the page (his 11-17: "no option to right-click and add a button"): add a button or
        paste the copied one, at the cell under the mouse; editing on or off."""
        ui.context.slot.parent.on("contextmenu", js_handler=PICK_CELL)
        copied = self._user.get(CLIPBOARD_KEY)
        with ui.context_menu():
            self._edit_switch_item()
            ui.menu_item("Add button here", on_click=lambda: self._edit(page, None, self._spot)).props("dense")
            paste = ui.menu_item("Paste button here" + (f": {copied.get('label', '')}" if copied else ""),
                                 on_click=lambda: self._paste(page, self._spot)).props("dense")
            if not copied:
                paste.disable()

    def _edit_switch_item(self) -> None:
        """The first line of a right-click menu: the pencil / check mark of the bar."""
        ui.menu_item("Done editing" if self._editing else "Edit the buttons", on_click=self._toggle_edit) \
            .props("dense").classes("font-semibold")
        ui.separator()

    def _picked(self, cell: dict[str, Any]) -> None:
        self._spot = (int(cell.get("x", 0)), int(cell.get("y", 0)))

    def _copy(self, page: DeckPage, index: int) -> None:
        """Keeps the button (this browser) to paste on any page (his 11-17: "copy a button and post it in a
        different page")."""
        self._user[CLIPBOARD_KEY] = page.buttons[index].to_dict()
        ui.notify(f"Copied {page.buttons[index].label}: right-click a free spot on any page, Paste button here")
        self._view.refresh()  # the page's menu offers it now

    def _paste(self, page: DeckPage, spot: tuple[int, int] | None) -> None:
        copied = self._user.get(CLIPBOARD_KEY)
        if not copied:
            return
        self._add(page, DeckButton.from_dict(copied), spot)
        self._save()

    @staticmethod
    def _add(page: DeckPage, button: DeckButton, spot: tuple[int, int] | None) -> None:
        """Puts a button on the page: at the cell (it stays inside the page), or the first free spot."""
        button.x = button.y = -1
        page.buttons.append(button)
        if spot is None:
            page.place()
        else:
            page.put(len(page.buttons) - 1, spot[0], spot[1], button.w, button.h)

    def _cut(self, page: DeckPage, index: int) -> None:
        self._user[CLIPBOARD_KEY] = page.buttons[index].to_dict()
        ui.notify(f"Cut {page.buttons.pop(index).label}: right-click a free spot on any page, Paste button here")
        self._save()

    async def _move_to_page(self, page: DeckPage, index: int) -> None:
        """To the first free spot of another page."""
        with ui.dialog() as dialog, ui.card().classes("w-80"):
            ui.label(f"Move {page.buttons[index].label} to").classes("font-semibold")
            for other in self._deck.pages:
                if other is not page:
                    ui.button(other.name, on_click=lambda o=other: dialog.submit(o)) \
                        .props("flat no-caps align=left").classes("w-full")
            ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps").classes("self-end")
        target = await dialog
        if not dialog.is_deleted:
            dialog.delete()
        if target is None or index >= len(page.buttons):
            return
        self._add(target, page.buttons.pop(index), None)
        self._save()
        ui.notify(f"Moved to {target.name}")

    def _start_swap(self, index: int) -> None:
        self._swapping = index
        if not self._bare:
            self._editing = True
            self._user[EDIT_KEY] = True
        ui.notify("Click the button it swaps places with (Esc: cancel)")
        self._view.refresh()

    def _swap_with(self, page: DeckPage, index: int) -> None:
        first, self._swapping = self._swapping, None
        if first is not None and first != index and first < len(page.buttons):
            a, b = page.buttons[first], page.buttons[index]
            (a.x, a.y), (b.x, b.y) = (b.x, b.y), (a.x, a.y)
            page.put(first, a.x, a.y, a.w, a.h)  # a bigger one moved near the edge stays inside
            page.put(index, b.x, b.y, b.w, b.h)
            self._save()
            return
        self._view.refresh()

    def _undo(self) -> None:
        names = [p.name for p in self._deck.pages]
        if not self._store.undo():
            ui.notify("Nothing to undo")
            return
        self._deck = self._store.load()
        self._seen = self._store.version
        if not self._deck.page(self._page):
            self._page = self._deck.pages[0].name if self._deck.pages else ""
        if [p.name for p in self._deck.pages] != names and not self._bare:
            ui.navigate.to(self.address(self._page) + "&edit=1")  # the side list follows
            return
        self._view.refresh()

    async def _key(self, pressed: dict[str, Any]) -> None:
        """A key while editing (live_deck.js): on the button under the mouse, or at the cell under it."""
        page = self._deck.page(self._page)
        if not self._editing or page is None:
            return
        key, index = str(pressed.get("key", "")), int(pressed.get("index", -1))
        x, y = int(pressed.get("x", -1)), int(pressed.get("y", -1))
        here = 0 <= index < len(page.buttons)
        if key == "Escape" and self._swapping is not None:
            self._swapping = None
            self._view.refresh()
        elif key == "z":
            self._undo()
        elif key == "c" and here:
            self._copy(page, index)
        elif key == "x" and here:
            self._cut(page, index)
        elif key == "v":
            self._paste(page, (x, y) if x >= 0 and y >= 0 else None)
        elif key in ("Delete", "Backspace") and here:
            await self._delete(page, index)

    def _duplicate(self, page: DeckPage, index: int) -> None:
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
            ui.button("Undo", icon="undo", on_click=self._undo).props("flat dense no-caps") \
                .tooltip("The deck as it was before the last change (Ctrl+Z)")
            ui.button("Page", icon="add", on_click=self._add_page).props("flat dense no-caps")
            if page:
                ui.button("Rename", icon="edit", on_click=lambda: self._rename_page(page)).props("flat dense no-caps")
                ui.button(icon="chevron_left", on_click=lambda: self._move_page(page, -1)) \
                    .props("flat round dense").tooltip("Move this page left")
                ui.button(icon="chevron_right", on_click=lambda: self._move_page(page, 1)) \
                    .props("flat round dense").tooltip("Move this page right")
                ui.button("Delete page", icon="delete", on_click=lambda: self._delete_page(page)) \
                    .props("flat dense no-caps color=negative")
            ui.label("Drag a button to move it, its corner to change its size; click it to change it; "
                     "right-click for more. Keys (mouse over a button or spot): Ctrl+C / X / V, Delete, Ctrl+Z; "
                     "Page Up / Down: pages") \
                .classes("text-xs opacity-60 pl-2")

    async def _add_page(self) -> None:
        name = await self._ask_name("New page", self._deck.free_page_name())
        if name:
            name = self._deck.free_page_name(name)
            self._deck.pages.append(DeckPage(name))
            self._page = name
            self._pages_changed()

    async def _rename_page(self, page: DeckPage) -> None:
        name = await self._ask_name("Rename page", page.name)
        if name and name != page.name:
            old, page.name = page.name, self._deck.free_page_name(name)
            for other in self._deck.pages:  # the buttons that go to it follow
                for button in other.buttons:
                    if button.action == GO_TO_PAGE and button.params.get("page") == old:
                        button.params["page"] = page.name
            self._page = page.name
            self._pages_changed()

    def _move_page(self, page: DeckPage, by: int) -> None:
        pages = self._deck.pages
        index = pages.index(page)
        target = max(0, min(len(pages) - 1, index + by))
        pages.insert(target, pages.pop(index))
        self._pages_changed()

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
        self._pages_changed()

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
