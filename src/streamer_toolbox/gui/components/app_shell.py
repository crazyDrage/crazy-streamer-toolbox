from collections.abc import Callable

from nicegui import app, ui

from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.gui.services.open_pages import OpenPages
from streamer_toolbox.gui.services.ui_registry import UiRegistry

# the core areas: (title, path, Material icon)
AREAS = [
    ("Live", "/", "bolt"),
    ("Flows", "/flows", "account_tree"),
    ("Triggers", "/triggers", "sensors"),
    ("Variables", "/variables", "data_object"),
    ("Overlay", "/overlays", "layers"),
    ("Tools", "/tools", "handyman"),
    ("Connections", "/connections", "hub"),
    ("Plugins", "/plugins", "extension"),
    ("Settings", "/settings", "tune"),
]
THEMES = {"auto": None, "dark": True, "light": False}
PRIMARY = "#6d5dfc"
HIDDEN_KEY = "menu_hidden"  # app.storage.general: the addresses of the menu items he hid
SHOW_ALL_KEY = "menu_show_all"  # app.storage.general: the menu shows the hidden ones too, with their eyes
SubItems = list[tuple[str, str, str]]
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


class AppShell:
    """The frame around every page, core or plugin: header, side menu (desktop), bottom tabs (phone).

    `sub_items` gives an area of the side menu a list below it: area path → (title, path, icon) per item, or a
    function that gives them when a page is drawn (Connections → one per connection, Overlay → its parts,
    Tools → one per tool). A click on the area's row opens the area's own page (its main view); only the
    arrow at the end of the row opens and closes the list. The list is open when one of its pages is shown,
    and whether he opened or closed it is remembered.

    Every item can be hidden: "Show all" at the bottom of the menu shows the hidden ones too (dimmed) and gives
    every item an eye to hide it or bring it back; with it off the hidden ones are gone, on the phone's bottom
    tabs too. The page being shown is always in the menu.

    `left_out` holds the addresses a build doesn't have because they are not tested yet (TestGate): they are in
    no menu, whatever "Show all" says, and opening one shows a line instead of the page. An area that is left
    out keeps its row while something below it is still there."""

    def __init__(self, ui_registry: UiRegistry, pages: OpenPages) -> None:
        self._ui = ui_registry
        self._pages = pages
        self.sub_items: dict[str, SubItems | Callable[[], SubItems]] = {}
        self.left_out: set[str] = set()

    @staticmethod
    def theme() -> str:
        return app.storage.general.get("theme", "dark")

    def page(self, title: str, path: str, builder: Callable[[], None]) -> None:
        ui.page(path, title=f"{title} · {APP_NAME}")(lambda: self.frame(title, path, builder))

    def frame(self, title: str, path: str, builder: Callable[[], None]) -> None:
        self._pages.attach(ui.context.client)
        ui.dark_mode(THEMES.get(self.theme()))
        ui.colors(primary=PRIMARY)
        ui.add_css(".tb-nav .q-item { border-radius: 8px; margin: 2px 8px; }"
                   ".tb-nav .tb-hidden { opacity: 0.45; }"
                   ".tb-tabs { background: #fff; } .body--dark .tb-tabs { background: #1d1d1d; }")

        drawer = ui.left_drawer(value=None, bordered=True).props("width=220").classes("tb-nav p-0")
        with ui.header().classes("items-center px-3 py-2 gap-2"):
            ui.button(icon="menu", on_click=drawer.toggle).props("flat round color=white") \
                .classes("lg:hidden").tooltip("Menu")
            ui.icon("construction").classes("text-xl")
            ui.label(APP_NAME).classes("text-lg font-semibold")
            ui.space()
            ui.label(title).classes("text-sm opacity-80 lg:hidden")

        here = self._here(path)

        @ui.refreshable
        def menu() -> None:
            self._menu(path, here, menu.refresh)

        with drawer:
            menu()
        ui.add_body_html(f"<script>{KEEP_MENU_SCROLL}</script>")

        # phone and tablet: the core areas as bottom tabs, within thumb reach
        with ui.footer().classes("tb-tabs lg:hidden p-0 border-t border-gray-500/30"):
            with ui.row().classes("w-full justify-around no-wrap gap-0"):
                for area_title, area_path, icon in AREAS:
                    active = area_path == path
                    if not self.offers(area_path) or (area_path in _hidden() and not active):
                        continue
                    ui.button(area_title, icon=icon).props(
                        f"flat stack no-caps href={area_path} color={'primary' if active else 'grey-6'}"
                    ).classes("flex-1 min-w-0 px-0 py-1 text-[11px]")

        with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
            ui.label(title).classes("text-2xl font-semibold max-lg:hidden")
            if not self.offers(here):
                ui.label("This page is not in this build: it has not been tested yet.").classes("opacity-70")
            else:
                builder()

    @staticmethod
    def _here(path: str) -> str:
        """The page being shown, with its ?show=... if it has one (a sub item's address)."""
        shown = ui.context.client.request.query_params.get("show", "")
        return f"{path}?show={shown}" if shown else path

    def _menu(self, path: str, here: str, redraw: Callable[[], None]) -> None:
        """The side menu. redraw: draws it again (after an eye or "Show all" was clicked)."""
        hidden = _hidden()
        show_all = bool(app.storage.general.get(SHOW_ALL_KEY, False))

        def there(item_path: str, active: bool) -> bool:
            return self.in_menu(item_path) and (show_all or active or item_path not in hidden)

        with ui.list().classes("w-full pt-2"):
            for area_title, area_path, icon in AREAS:
                if not there(area_path, area_path == path):
                    continue
                if area_path in self.sub_items:
                    self._nav_group(area_title, area_path, icon, here, show_all, redraw)
                else:
                    self._nav_item(area_title, area_path, icon, area_path == path, show_all=show_all, redraw=redraw)
            plugin_pages = [page for page in self._ui.pages if there(page[1], page[1] == path)]
            if plugin_pages:
                ui.separator().classes("my-2")
                ui.item_label("Plugin pages").props("header").classes("text-xs uppercase py-1")
                for page_title, page_path, icon in plugin_pages:
                    self._nav_item(page_title, page_path, icon, page_path == path, show_all=show_all, redraw=redraw)
            ui.separator().classes("my-2")
            with ui.item().classes("text-xs opacity-80"):
                with ui.item_section():
                    ui.switch("Show all" + (f" ({len(hidden)} hidden)" if hidden else ""), value=show_all,
                              on_change=lambda e: (app.storage.general.update({SHOW_ALL_KEY: e.value}), redraw())) \
                        .props("dense size=sm") \
                        .tooltip("On: the menu shows every item, and each has an eye to hide it or bring it back. "
                                 "Off: the hidden ones are gone")

    def _nav_group(self, title: str, path: str, icon: str, here: str, show_all: bool,
                   redraw: Callable[[], None]) -> None:
        """An area with sub items: the row opens the area's own page, the arrow on it the list below."""
        items = self._below(path)
        hidden = _hidden()
        inside = here.split("?", 1)[0] == path
        key = f"menu_open:{path}"
        opened = bool(app.storage.general.get(key, False)) or inside

        def flip() -> None:
            sub_list.set_visibility(not sub_list.visible)
            app.storage.general[key] = sub_list.visible
            arrow.set_icon(_arrow(sub_list.visible))

        with ui.item().props(f"clickable href={path}" + (" active active-class=bg-primary/20" if here == path
                                                         else "")) \
                .classes(("text-primary" if inside else "") + (" tb-hidden" if path in hidden else "")):
            with ui.item_section().props("avatar").classes("min-w-0 pr-3"):
                ui.icon(icon)
            with ui.item_section():
                ui.label(title)
            if show_all:
                _eye(path, path in hidden, redraw)
            with ui.item_section().props("side"):
                arrow = ui.button(icon=_arrow(opened)).props("flat round dense size=sm") \
                    .on("click.stop.prevent", flip).tooltip(f"Show or hide what is under {title}")
        with ui.list().props("dense").classes("w-full p-0") as sub_list:
            for sub_title, sub_path, sub_icon in items:
                if show_all or here == sub_path or sub_path not in hidden:
                    self._nav_item(sub_title, sub_path, sub_icon, here == sub_path, sub=True,
                                   show_all=show_all, redraw=redraw)
        sub_list.set_visibility(opened)

    def offers(self, address: str) -> bool:
        """Whether this copy has the page at that address (with its ?show=... for a sub item)."""
        return address not in self.left_out

    def in_menu(self, path: str) -> bool:
        """Whether the menu may list it: this copy has it, or it is an area with something left below it."""
        return self.offers(path) or bool(self._below(path))

    def _below(self, path: str) -> SubItems:
        """An area's sub items that this copy has."""
        given = self.sub_items.get(path, [])
        return [item for item in (given() if callable(given) else given) if item[1] not in self.left_out]

    @staticmethod
    def _nav_item(title: str, path: str, icon: str, active: bool, sub: bool = False, show_all: bool = False,
                  redraw: Callable[[], None] | None = None) -> None:
        is_hidden = path in _hidden()
        with ui.item().props(f"clickable href={path}" + (" active active-class=bg-primary/20" if active else "")
                             + (" dense" if sub else "")) \
                .classes(("text-primary" if active else "") + (" pl-6 text-sm" if sub else "")
                         + (" tb-hidden" if is_hidden else "")):
            with ui.item_section().props("avatar").classes("min-w-0 pr-3"):
                ui.icon(icon).classes("text-lg" if sub else "")
            with ui.item_section():
                ui.label(title)
            if show_all and redraw is not None:
                _eye(path, is_hidden, redraw)


def _arrow(opened: bool) -> str:
    return "expand_less" if opened else "expand_more"


def _hidden() -> list[str]:
    hidden = app.storage.general.get(HIDDEN_KEY, [])
    return hidden if isinstance(hidden, list) else []


def _eye(path: str, is_hidden: bool, redraw: Callable[[], None]) -> None:
    """The eye on a menu item while "Show all" is on: hides the item, or brings a hidden one back."""
    def flip() -> None:
        hidden = [p for p in _hidden() if p != path]
        app.storage.general[HIDDEN_KEY] = hidden if is_hidden else [*hidden, path]
        redraw()

    with ui.item_section().props("side"):
        ui.button(icon="visibility_off" if is_hidden else "visibility").props("flat round dense size=sm") \
            .on("click.stop.prevent", flip).tooltip("Show it in the menu again" if is_hidden else "Hide it")
