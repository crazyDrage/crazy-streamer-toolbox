import logging
from collections.abc import Callable

from nicegui import background_tasks, ui

from streamer_toolbox.core.app_version import is_newer, version_numbers
from streamer_toolbox.core.system.toolbox_restart import ToolboxRestart
from streamer_toolbox.gui.components.header_notice import HeaderNotice
from streamer_toolbox.gui.components.type_chips import TypeChips
from streamer_toolbox.plugins.listed_plugin import ListedPlugin
from streamer_toolbox.plugins.listing_addresses import FILE_NAME, MAIN_LISTING
from streamer_toolbox.plugins.plugin_installer import PluginInstaller
from streamer_toolbox.plugins.plugin_listings import PluginListings
from streamer_toolbox.plugins.plugin_systems import runs_here, system_names

log = logging.getLogger(__name__)
ADDRESS = "/plugins?show=get-plugins"  # a plugin id can't have a "-": no plugin's own row is called that
NOTICE = "plugin_updates"


class PluginListingPanel:
    """Plugins → Get plugins (his next release plan, part 4): the plugins of every listing file, each with
    Install (or Update to a newer version), and the listing files themselves (his answer: "a setting ... where
    we can set multiple listing files"). A plugin is code from the internet: Install asks first, and says so
    louder for one that isn't from the main listing. It loads at the next start: the page says so and offers
    Restart (no popup in the way: his note of 2026-11-01).

    Added 2026-11-02 (his "you can work on the points you don't need me"): type chips and a search, Remove
    (the folder is kept), Other versions (back to an older one), what's new, "Only for Windows", "Needs the
    plugin x first", and at the start (when "Look for updates" is on) "Plugin updates (n)" next to the
    toolbox's name."""

    def __init__(self, listings: PluginListings, installer: PluginInstaller, restart: ToolboxRestart,
                 notices: dict[str, HeaderNotice] | None = None, check: Callable[[], bool] = lambda: False) -> None:
        self._listings = listings
        self._installer = installer
        self._restart = restart
        self._notices = notices if notices is not None else {}
        self._check = check  # Settings → General → "Look for updates by itself": the plugins are asked too
        self._plugins: list[ListedPlugin] | None = None  # None: not read yet
        self._problems: list[str] = []
        self._done_now: list[str] = []  # "Installed Jokes", "Removed Dice": they count after a restart
        self.removed: set[str] = set()  # plugin ids removed since the start (still loaded until a restart)
        self._chips = TypeChips(lambda: self._list.refresh())
        self._search = ""

    def start(self) -> None:
        """At the toolbox's start: read the listings once in the background, for "Plugin updates (n)"."""
        if self._check():
            background_tasks.create(self._read(), name="plugin listings")

    def build(self) -> None:
        ui.label("Get plugins").classes("text-xl font-semibold")
        ui.label("Plugins from the listing files below. A plugin is code from the internet: it can do everything "
                 "the toolbox can. Install only what you trust.").classes("text-sm opacity-80")
        self.restart_line()
        with ui.input("Search", on_change=lambda e: self._searched(e.value)).props("outlined dense clearable") \
                .classes("w-full sm:w-80").add_slot("prepend"):
            ui.icon("search")
        self._list()
        with ui.card().classes("w-full mt-4"):
            self._addresses()
        ui.timer(0.1, self._read, once=True)

    @ui.refreshable_method
    def restart_line(self) -> None:
        """What was installed or removed since the start, with Restart (also on the Plugins overview)."""
        if not self._done_now:
            return
        with ui.row().classes("items-center gap-2 w-full"):
            ui.label(f"{'. '.join(self._done_now)}. That counts when the toolbox starts again.") \
                .classes("text-sm text-positive font-medium")
            if self._restart.available:
                ui.button("Restart now", icon="restart_alt",
                          on_click=lambda: ui.timer(0.3, self._restart.request, once=True)) \
                    .props("unelevated no-caps dense")

    @ui.refreshable_method
    def _list(self) -> None:
        with ui.row().classes("items-center gap-2"):
            ui.button("Read the listings again", icon="refresh", on_click=self._read).props("outline no-caps dense")
            if self._plugins is None:
                ui.spinner(size="sm")
        for problem in self._problems:
            ui.label(problem).classes("text-sm text-warning break-words")
        if self._plugins is not None and not self._plugins:
            ui.label("No plugins in the listings.").classes("text-sm opacity-70")
        self._chips.build([p.types for p in self._plugins or []])
        shown = [p for p in self._plugins or [] if self._fits(p)]
        if self._plugins and not shown:
            ui.label("No plugin fits.").classes("text-sm opacity-70")
        installed = self._installer.installed()
        with ui.element("div").classes("grid gap-4 w-full items-start sm:grid-cols-2 lg:grid-cols-3"):
            for plugin in shown:
                self._card(plugin, installed)

    def _searched(self, text: str | None) -> None:
        self._search = (text or "").strip().casefold()
        self._list.refresh()

    def _fits(self, plugin: ListedPlugin) -> bool:
        words = " ".join((plugin.name, plugin.id, plugin.about, plugin.author)).casefold()
        return self._chips.fits(plugin.types) and self._search in words

    def _card(self, plugin: ListedPlugin, installed: dict[str, str]) -> None:
        have = installed.get(plugin.id)
        with ui.card().classes("w-full gap-1"):
            with ui.row().classes("w-full items-center no-wrap gap-2"):
                ui.icon("extension").classes("text-xl text-primary")
                ui.label(plugin.name).classes("font-semibold min-w-0 break-words")
                ui.space()
                ui.label(plugin.version).classes("text-xs opacity-70 font-mono")
            if plugin.about:
                ui.label(plugin.about).classes("text-sm break-words")
            TypeChips.badges(plugin.types)
            by = f"by {plugin.author} · " if plugin.author else ""
            ui.label(f"{by}from {', '.join(plugin.listings)}").classes("text-xs opacity-60 break-words")
            newer = have is not None and version_numbers(plugin.version) > version_numbers(have)
            if plugin.changes and (have is None or newer):
                ui.label(f"New in {plugin.version}: {plugin.changes}").classes("text-xs break-words")
            missing = [self._name(n) for n in plugin.needs if n not in installed]
            with ui.row().classes("items-center gap-2"):
                if not runs_here(plugin.systems):
                    ui.label(f"Only for {system_names(plugin.systems)}").classes("text-xs text-warning")
                elif plugin.toolbox and is_newer(plugin.toolbox):
                    ui.label(f"Needs toolbox {plugin.toolbox} or newer").classes("text-xs text-warning")
                elif missing and (have is None or newer):
                    ui.label(f"Needs the plugin {', '.join(missing)} first").classes("text-xs text-warning")
                elif have is None:
                    ui.button("Install", icon="download", on_click=lambda p=plugin: self._ask(p)) \
                        .props("unelevated no-caps dense")
                elif newer:
                    ui.button(f"Update to {plugin.version}", icon="system_update",
                              on_click=lambda p=plugin: self._ask(p, have)).props("unelevated no-caps dense")
                    ui.label(f"you have {have}").classes("text-xs opacity-60")
                else:
                    ui.label(f"Installed ({have})").classes("text-xs text-positive")
                if plugin.page:
                    # not put into .props(): a listing's text must never become a prop
                    ui.button("Its page", icon="open_in_new",
                              on_click=lambda p=plugin.page: ui.navigate.to(p, new_tab=True)) \
                        .props("flat no-caps dense")
                self._more(plugin, have)

    def _more(self, plugin: ListedPlugin, have: str | None) -> None:
        """The ⋮ menu: other versions to install instead, and Remove."""
        others = self._listings.others(plugin.id, have or plugin.version)
        if have is not None and version_numbers(have) != version_numbers(plugin.version):
            others = [p for p in others if version_numbers(p.version) != version_numbers(plugin.version)]
        if not others and have is None:
            return
        with ui.button(icon="more_vert").props("flat round dense aria-label=More"):
            with ui.menu():
                for other in others:
                    ui.menu_item(f"Install {other.version} instead", on_click=lambda p=other: self._ask(p, have))
                if have is not None:
                    ui.menu_item("Remove", on_click=lambda: self.ask_remove(plugin.id, plugin.name))

    def _name(self, plugin_id: str) -> str:
        return next((p.name for p in self._plugins or [] if p.id == plugin_id), plugin_id)

    def _ask(self, plugin: ListedPlugin, have: str | None = None) -> None:
        if have is None:
            title = f"Install {plugin.name} {plugin.version}?"
        elif version_numbers(plugin.version) > version_numbers(have):
            title = f"Update {plugin.name} to {plugin.version}?"
        else:
            title = f"Go back to {plugin.name} {plugin.version}?"
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-3"):
            ui.label(title).classes("text-lg font-semibold")
            ui.label("A plugin is code from the internet. Once it runs it can do everything the toolbox can: "
                     "your flows, your connections, your files.").classes("text-sm")
            by = f" by {plugin.author}" if plugin.author else ""
            ui.label(f"It is{by}, from {', '.join(plugin.listings)}.").classes("text-sm opacity-80")
            if not plugin.official:
                ui.label("It isn't from the main listing: nobody checked it for the toolbox. Install it only "
                         "when you know who made it.").classes("text-sm text-warning")
            if plugin.changes:
                ui.label(f"New in {plugin.version}: {plugin.changes}").classes("text-sm break-words")
            if have is not None:
                ui.label(f"Your {have} is kept in the settings folder's cache/plugins/kept.") \
                    .classes("text-xs opacity-70")
            said = ui.label("").classes("text-sm text-negative break-words")

            async def install() -> None:
                button.disable()
                said.set_text("")
                try:
                    await self._installer.install(plugin)
                except Exception as e:
                    said.set_text(f"Not installed: {e}")
                    button.enable()
                    return
                dialog.close()
                self._done(f"Installed {plugin.name} {plugin.version}")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
                button = ui.button("Install", icon="download", on_click=install).props("unelevated no-caps")
        dialog.open()

    def ask_remove(self, plugin_id: str, name: str, after: Callable[[], None] = lambda: None) -> None:
        """Asks, then takes the plugin out of the plugins folder (also from the Plugins overview: `after`)."""
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-3"):
            ui.label(f"Remove {name}?").classes("text-lg font-semibold")
            ui.label("It stops when the toolbox starts again. Its boxes stay in your flows (they don't run without "
                     "it); its settings and keys stay too, for when you install it again.").classes("text-sm")
            ui.label("Its folder is kept in the settings folder's cache/plugins/kept.").classes("text-xs opacity-70")
            said = ui.label("").classes("text-sm text-negative break-words")

            def remove() -> None:
                try:
                    self._installer.remove(plugin_id)
                except (OSError, RuntimeError) as e:
                    said.set_text(f"Not removed: {e}")
                    return
                dialog.close()
                self.removed.add(plugin_id)
                self._done(f"Removed {name}")
                after()

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
                ui.button("Remove", icon="delete", on_click=remove).props("unelevated no-caps color=negative")
        dialog.open()

    def _done(self, what: str) -> None:
        self._done_now.append(what)
        self.restart_line.refresh()
        self._list.refresh()
        self._show_updates()

    @ui.refreshable_method
    def _addresses(self) -> None:
        ui.label("Listing files").classes("text-lg font-semibold")
        ui.label("Where the plugins above come from: web addresses or files on this PC. Add your own when the "
                 "main one stops working.").classes("text-sm opacity-80")
        ui.label(f"Kept in {FILE_NAME} in the settings folder: one address per line, lines starting with # are "
                 "notes.").classes("text-xs opacity-60")
        for address in self._listings.addresses:
            with ui.row().classes("items-center no-wrap gap-2 w-full"):
                ui.label(address).classes("text-sm font-mono break-all flex-1 min-w-0")
                if address == MAIN_LISTING:
                    ui.badge("main").props("color=primary")
                ui.button(icon="close", on_click=lambda a=address: self._remove(a)) \
                    .props("flat round dense").tooltip("Not from this listing any more")
        if not self._listings.addresses:
            ui.label("No listing files: no plugins to get.").classes("text-sm text-warning")
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            field = ui.input("Add a listing file", placeholder="https://... or C:\\...\\plugins.toml") \
                .props("outlined dense").classes("flex-1 min-w-0")
            ui.button("Add", icon="add", on_click=lambda: self._add(field)).props("unelevated no-caps")
        if MAIN_LISTING not in self._listings.addresses:
            ui.button("Put the main one back", icon="undo", on_click=self._main_back).props("flat no-caps dense")

    async def _add(self, field: ui.input) -> None:
        try:
            self._listings.add(field.value or "")
        except ValueError as e:
            field.props["error"] = True  # set as values: a typed address with " or spaces can't add props
            field.props["error-message"] = str(e)
            field.update()
            return
        self._addresses.refresh()
        await self._read()

    async def _remove(self, address: str) -> None:
        self._listings.remove(address)
        self._addresses.refresh()
        await self._read()

    async def _main_back(self) -> None:
        self._listings.put_main_back()
        self._addresses.refresh()
        await self._read()

    async def _read(self) -> None:
        self._plugins = None
        self._list.refresh()
        try:
            self._plugins, self._problems = await self._listings.fetch()
        except Exception as e:  # at the start nobody would see it otherwise
            log.warning("plugin listings: %s", e)
            self._plugins, self._problems = [], [f"The listings couldn't be read: {e}"]
        self._list.refresh()
        self._show_updates()

    def _show_updates(self) -> None:
        """ "Plugin updates (n)" next to the toolbox's name while installed plugins have a newer version."""
        installed = self._installer.installed()
        updates = [p for p in self._plugins or [] if p.id in installed and runs_here(p.systems)
                   and not (p.toolbox and is_newer(p.toolbox))
                   and version_numbers(p.version) > version_numbers(installed[p.id])]
        if not updates:
            self._notices.pop(NOTICE, None)
            return
        self._notices[NOTICE] = HeaderNotice(f"Plugin updates ({len(updates)})", "", icon="extension",
                                             on_press=lambda: ui.navigate.to(ADDRESS), color="primary")
