from collections.abc import Callable
from urllib.parse import quote

from nicegui import app, ui

from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.gui.components.look import Look
from streamer_toolbox.gui.services.open_pages import OpenPages
from streamer_toolbox.gui.services.ui_registry import UiRegistry

# the core areas: (title, path, Material icon)
AREAS = [
    ("Live", "/", "bolt"),
    ("Flows", "/flows", "account_tree"),
    ("Variables", "/variables", "data_object"),
    ("Overlay", "/overlays", "layers"),
    ("Tools", "/tools", "handyman"),
    ("Connections", "/connections", "hub"),
    ("Plugins", "/plugins", "extension"),
    ("Settings", "/settings", "tune"),
]
PLUGINS = "/plugins"  # the area a plugin's own pages (/plugins/<id>...) are shown in
HIDDEN_KEY = "menu_hidden"  # app.storage.general: the addresses of the menu items he hid
SHOW_ALL_KEY = "menu_show_all"  # app.storage.general: the menu shows the hidden ones too, with their eyes
OPEN_KEY = "menu_open"  # app.storage.general: side row address → its sub rows are shown (True) or folded (False)
# (title, address, icon) per side row; a 4th value True makes it a sub row, drawn in under the row before it
SubItems = list[tuple[str, str, str] | tuple[str, str, str, bool]]
# draws something at the bottom of an area's side list (Flows: New folder); gets the function that redraws the list
SideTool = Callable[[Callable[[], None]], None]
# every menu click loads a new page, and a new page's menu starts at its top: with a long menu (the list of
# connections) he had to scroll down again after each click. The browser tab remembers how far the menu was
# scrolled and the next page puts it back there (waits until the menu's rows are drawn)
KEEP_MENU_SCROLL = """
(() => {
  const KEY = 'tb-menu-scroll';
  let tries = 0;
  const timer = setInterval(() => {
    const box = document.querySelector('.q-drawer--left .q-drawer__content');
    if (++tries > 100) clearInterval(timer);
    if (!box || !box.querySelector('.q-item')) return;
    clearInterval(timer);
    box.scrollTop = Number(sessionStorage.getItem(KEY) || 0);
    box.addEventListener('scroll', () => sessionStorage.setItem(KEY, box.scrollTop), {passive: true});
  }, 30);
})();
"""

# the header's height as --tb-head, so a page's top part (.tb-sticky, the Flows page's buttons) stays right under
# it while the page scrolls; the header grows when its tabs wrap to a new line
HEADER_HEIGHT = """
(() => {
  let tries = 0;
  const timer = setInterval(() => {
    const header = document.querySelector('.q-header');
    if (++tries > 100) clearInterval(timer);
    if (!header) return;
    clearInterval(timer);
    const set = () => document.documentElement.style.setProperty('--tb-head', header.offsetHeight + 'px');
    new ResizeObserver(set).observe(header);
    set();
  }, 30);
})();
"""


class AppShell:
    """The frame around every page, core or plugin (his layout of 2026-10-12: main tabs on top, sub tabs on
    the side): the header holds the areas as tabs (a new line when they don't fit, never a scroll bar); the
    side list holds what is under the area being shown; on a phone the tabs are a line of their own in the
    header (on top too, his wish) and the side list slides in from the menu button (there it also lists the
    areas).

    `sub_items` gives an area its side list: area path → (title, path, icon) per item, or a function that gives
    them when a page is drawn (Connections → one per connection, Overlay → its parts, Tools → one per tool,
    Plugins → a row per plugin with its pages as sub rows; a plugin's page is no tab, it is shown inside the
    Plugins area).
    Its first row, Overview, is the area's own page. An area without sub items has no side list. A row with sub
    rows has an arrow that folds them away or shows them (his wish of 2026-10-16); it starts open when the page
    being shown is in it, and a fold he made is kept. `side_tools` adds something at the bottom of an area's
    side list. A page below an area (/flows/edit) is shown in that area, with its side list; on a wide screen
    the menu button slides the side list away and back.

    Every item can be hidden: the eye in the header ("Show all") shows the hidden ones too (dimmed) and gives
    every tab and item an eye to hide it or bring it back; with it off the hidden ones are gone, on the
    phone's bottom tabs too. The page being shown is always there."""

    def __init__(self, ui_registry: UiRegistry, pages: OpenPages) -> None:
        self._ui = ui_registry
        self._pages = pages
        self.sub_items: dict[str, SubItems | Callable[[], SubItems]] = {PLUGINS: lambda: list(ui_registry.pages)}
        self.side_tools: dict[str, SideTool] = {}

    @staticmethod
    def theme() -> str:
        return app.storage.general.get("theme", "dark")

    def page(self, title: str, path: str, builder: Callable[[], None]) -> None:
        ui.page(path, title=f"{title} · {APP_NAME}")(lambda: self.frame(title, path, builder))

    def bare(self, title: str, path: str, builder: Callable[[], None]) -> None:
        """A page without the frame: no header, no side list (the Live buttons on their own)."""
        @ui.page(path, title=f"{title} · {APP_NAME}")
        def page() -> None:
            self._pages.attach(ui.context.client)
            Look.apply(self.theme())
            with ui.column().classes("w-full p-2 gap-2"):
                builder()

    def frame(self, title: str, path: str, builder: Callable[[], None]) -> None:
        self._pages.attach(ui.context.client)
        Look.apply(self.theme())

        here = self._here(path)
        area = self.area(path)

        def redraw() -> None:
            tabs.refresh()
            phone_tabs.refresh()
            menu.refresh()

        @ui.refreshable
        def tabs() -> None:
            self._tabs(area, redraw)

        @ui.refreshable
        def phone_tabs() -> None:
            self._phone_tabs(area)

        @ui.refreshable
        def menu() -> None:
            self._menu(area, here, redraw)

        # the side list is there on a wide screen only when the area has something under it; on a phone it
        # slides in from the menu button and also lists the areas
        side = bool(self._below(area)) or area in self.side_tools
        drawer = ui.left_drawer(value=None if side else False, bordered=True).props("width=220") \
            .classes("tb-nav p-0")
        # the app name is a line of its own on top (his answer of 2026-10-14), the tabs are the line below
        with ui.header().classes("flex-col items-stretch px-3 pt-1 pb-0 gap-0"):
            with ui.row().classes("tb-name-line w-full items-center gap-2 no-wrap"):
                ui.button(icon="menu", on_click=drawer.toggle).props("flat round dense color=white") \
                    .classes("" if side else "lg:hidden").tooltip("Menu (slides the side list away and back)")
                ui.icon("construction").classes("text-sm opacity-70")
                ui.label(APP_NAME).classes("tb-name")
                ui.space()
                ui.label(title).classes("text-sm opacity-80 lg:hidden")
                ui.button(icon="visibility", on_click=lambda: (app.storage.general.update(
                    {SHOW_ALL_KEY: not app.storage.general.get(SHOW_ALL_KEY, False)}), redraw())) \
                    .props("flat round dense color=white size=sm").classes("opacity-70") \
                    .tooltip("Show all: every tab and item, each with an eye to hide it or bring it back. "
                             "Press again and the hidden ones are gone")
            with ui.row().classes("tb-top max-lg:hidden items-end gap-0 w-full"):
                tabs()
            # phone and tablet: the tabs stay on top too (his wish of 2026-10-14), a line of their own
            with ui.row().classes("tb-top tb-top-phone lg:hidden w-full gap-0"):
                phone_tabs()

        with drawer:
            menu()
        ui.add_body_html(f"<script>{KEEP_MENU_SCROLL}{HEADER_HEIGHT}</script>")

        with ui.column().classes("w-full max-w-7xl mx-auto p-4 gap-4"):
            ui.label(title).classes("text-2xl font-semibold max-lg:hidden")
            builder()

    @staticmethod
    def _here(path: str) -> str:
        """The page being shown, with its ?show=... if it has one (a sub item's address; a name in it is
        written the way a link writes it, a space as %20)."""
        params = ui.context.client.request.query_params
        for key in ("show", "flow"):
            if params.get(key, ""):
                return f"{path}?{key}={quote(params[key], safe='')}"
        return path

    @staticmethod
    def area(path: str) -> str:
        """The area a page is shown in: its own address, or the area it is below (a plugin's page → Plugins,
        /flows/edit → Flows)."""
        above = [a[1] for a in AREAS if a[1] != "/" and path.startswith(a[1] + "/")]
        return max(above, key=len) if above else path

    def _shown(self, path: str) -> list[tuple[str, str, str]]:
        """The areas that are tabs now: the ones he didn't hide (the one being shown and, with "Show all", the
        hidden ones are there too)."""
        hidden = _hidden()
        show_all = bool(app.storage.general.get(SHOW_ALL_KEY, False))
        return [page for page in AREAS
                if show_all or page[1] == path or page[1] not in hidden]

    def _tabs(self, path: str, redraw: Callable[[], None]) -> None:
        """The main tabs in the header (a wide screen); path: the area being shown. redraw: after an eye was
        clicked."""
        hidden = _hidden()
        show_all = bool(app.storage.general.get(SHOW_ALL_KEY, False))
        for title, page_path, icon in self._shown(path):
            ui.button(title, icon=icon).props(f"flat no-caps dense color=white href={page_path}") \
                .classes("px-3 shrink-0" + (" tb-here" if page_path == path else "")
                         + (" tb-hidden" if page_path in hidden else ""))
            if show_all:
                _eye_button(page_path, page_path in hidden, redraw).props("color=white").classes("shrink-0")

    def _phone_tabs(self, path: str) -> None:
        """The main tabs on a narrow screen: icon over a short name, as many in a line as fit."""
        for title, page_path, icon in self._shown(path):
            ui.button(title, icon=icon).props(f"flat stack no-caps dense color=white href={page_path}") \
                .classes("flex-1 px-1" + (" tb-here" if page_path == path else ""))

    def _menu(self, path: str, here: str, redraw: Callable[[], None]) -> None:
        """The side list: what is under the area being shown (path); on a phone also the areas. here: the
        page being shown. redraw: draws it again (after an eye or "Show all" was clicked)."""
        hidden = _hidden()
        show_all = bool(app.storage.general.get(SHOW_ALL_KEY, False))
        below = self._below(path)
        with ui.list().classes("w-full pt-2"):
            if below:
                area = next((a for a in AREAS if a[1] == path), None)
                if area:
                    self._nav_item("Overview", path, area[2], here == path)
                for row, subs in _groups(below):
                    self._side_row(row, subs, here, hidden, show_all, redraw)
            if path in self.side_tools:
                self.side_tools[path](redraw)
        with ui.list().classes("w-full lg:hidden"):
            if below:
                ui.separator().classes("my-2")
            for title, page_path, icon in self._shown(path):
                self._nav_item(title, page_path, icon, page_path == path, show_all=show_all, redraw=redraw)

    def _side_row(self, row: tuple, subs: list[tuple], here: str, hidden: list[str], show_all: bool,
                  redraw: Callable[[], None]) -> None:
        """A side row and, unless folded, its sub rows."""
        def active(address: str) -> bool:
            # a plugin's further pages (/plugins/<id>/...) belong to its row
            return here == address or here.startswith(address + "/")

        title, address, icon = row[:3]
        inside = any(active(s[1]) for s in subs)
        if not (show_all or active(address) or inside or address not in hidden):
            return
        shown_subs = [s for s in subs if show_all or active(s[1]) or s[1] not in hidden]
        opened = _folds().get(address, active(address) or inside)

        def fold() -> None:
            app.storage.general[OPEN_KEY] = {**_folds(), address: not opened}
            redraw()

        self._nav_item(title, address, icon, active(address), show_all=show_all, redraw=redraw,
                       fold=(opened, fold) if shown_subs else None)
        if opened:
            for sub in shown_subs:
                self._nav_item(sub[0], sub[1], sub[2], active(sub[1]), sub=True, show_all=show_all, redraw=redraw)

    def _below(self, path: str) -> SubItems:
        """An area's sub items."""
        given = self.sub_items.get(path, [])
        return list(given() if callable(given) else given)

    @staticmethod
    def _nav_item(title: str, path: str, icon: str, active: bool, sub: bool = False, show_all: bool = False,
                  redraw: Callable[[], None] | None = None,
                  fold: tuple[bool, Callable[[], None]] | None = None) -> None:
        """A side row; fold: (open, flip) gives it the arrow that shows or folds away its sub rows."""
        is_hidden = path in _hidden()
        with ui.item().props(f"clickable href={path}" + (" active active-class=bg-primary/20" if active else "")
                             + (" dense" if sub else "")) \
                .classes(("text-primary" if active else "") + (" tb-sub" if sub else "")
                         + (" tb-hidden" if is_hidden else "")):
            with ui.item_section().props("avatar").classes("min-w-0 pr-3"):
                ui.icon(icon).classes("text-lg" if sub else "")
            with ui.item_section():
                ui.label(title)
            if show_all and redraw is not None:
                _eye(path, is_hidden, redraw)
            if fold:
                with ui.item_section().props("side"):
                    ui.button(icon="expand_less" if fold[0] else "expand_more").props("flat round dense size=sm") \
                        .on("click.stop.prevent", fold[1]).tooltip("Fold away" if fold[0] else "Show what is in it")


def _groups(items: SubItems) -> list[tuple[tuple, list[tuple]]]:
    """The side rows, each with the sub rows drawn in under it."""
    groups: list[tuple[tuple, list[tuple]]] = []
    for item in items:
        if len(item) > 3 and item[3] and groups:
            groups[-1][1].append(item)
        else:
            groups.append((item, []))
    return groups


def _folds() -> dict[str, bool]:
    folds = app.storage.general.get(OPEN_KEY, {})
    return folds if isinstance(folds, dict) else {}


def _hidden() -> list[str]:
    hidden = app.storage.general.get(HIDDEN_KEY, [])
    return hidden if isinstance(hidden, list) else []


def _eye(path: str, is_hidden: bool, redraw: Callable[[], None]) -> None:
    """The eye on a menu item while "Show all" is on: hides the item, or brings a hidden one back."""
    with ui.item_section().props("side"):
        _eye_button(path, is_hidden, redraw)


def _eye_button(path: str, is_hidden: bool, redraw: Callable[[], None]) -> ui.button:
    def flip() -> None:
        hidden = [p for p in _hidden() if p != path]
        app.storage.general[HIDDEN_KEY] = hidden if is_hidden else [*hidden, path]
        redraw()

    return ui.button(icon="visibility_off" if is_hidden else "visibility").props("flat round dense size=sm") \
        .on("click.stop.prevent", flip).tooltip("Show it again" if is_hidden else "Hide it")
