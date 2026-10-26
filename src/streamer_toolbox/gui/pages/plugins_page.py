from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.gui.components.secret_input import SecretInput
from streamer_toolbox.gui.services.ui_registry import UiRegistry
from streamer_toolbox.plugins.plugin_manifest import PluginManifest
from streamer_toolbox.plugins.plugin_power import PluginPower
from streamer_toolbox.plugins.plugin_switches import PluginSwitches
from streamer_toolbox.plugins.plugin_template import PluginTemplate

# loaded ids, failed id -> reason, disabled ids, folder manifests by id
PluginStatus = Callable[[], tuple[list[str], dict[str, str], list[str], dict[str, PluginManifest]]]
STATUS_COLOURS = {"loaded": "positive", "off": "grey", "failed": "negative", "disabled": "grey"}


class PluginsPage:
    """One card per plugin found: loaded, failed (with the reason) or disabled by the enable list. A loaded
    one has a switch: off stops everything of it (PluginPower; his round 57: "off stops everything, even if
    it is used in a box"); flows keep its boxes, which work again once it is on. The keys a plugin needs (ctx.secret) are typed on its card.

    The side list (side_items, his wish of 2026-10-14: "sub items on the side list") has a row per plugin,
    /plugins?show=<id>: its card and its panels (the "live" and "settings" ones; they are on neither Live nor
    Settings any more), and below it a row per page the plugin added."""

    def __init__(self, status: PluginStatus, ui_registry: UiRegistry, switches: PluginSwitches | None = None,
                 template: PluginTemplate | None = None, power: PluginPower | None = None) -> None:
        self._status = status
        self._ui = ui_registry
        self._switches = switches
        self._power = power  # what switching does (without it, only the switch is written)
        self._template = template  # the "New plugin" button

    def side_items(self) -> list[tuple[str, str, str] | tuple[str, str, str, bool]]:
        """(title, address, icon) per plugin, then (title, address, icon, True) per page of it (a sub row). A
        plugin that is off (switched off or disabled) is left out (his wish of 2026-10-16); the Overview still
        has its card, with the switch to turn it back on."""
        loaded, failed, _disabled, manifests = self._status()
        off = self._switches.off() if self._switches else set()
        items: list[tuple[str, str, str] | tuple[str, str, str, bool]] = []
        for plugin_id in [*[p for p in loaded if p not in off], *failed]:
            manifest = manifests.get(plugin_id)
            items.append((manifest.name if manifest else plugin_id, f"/plugins?show={plugin_id}", "extension"))
            items += [(title, path, icon, True) for title, path, icon in self._ui.pages
                      if _owner(path) == plugin_id]
        return items

    def build(self) -> None:
        show = ui.context.client.request.query_params.get("show", "")
        if show:
            self._one(show)
        else:
            self._all()

    @ui.refreshable_method
    def _one(self, plugin_id: str) -> None:
        """One plugin: its card and its panels."""
        self._cards(only=plugin_id)
        for owner, section, title, builder in self._ui.panels:
            if owner == plugin_id and section in ("live", "settings") and not self._ui.is_off(owner):
                with ui.card().classes("w-full"):
                    ui.label(title).classes("text-lg font-semibold")
                    builder()

    @ui.refreshable_method
    def _all(self) -> None:
        if self._template:
            ui.button("New plugin", icon="add", on_click=self._new).props("no-caps unelevated")
        self._cards()
        ui.label("Plugins live in the plugins folder. The switch takes effect at once. To not load a plugin at "
                 "all, list the ones you want in [plugins] enabled in the settings file (then boxes of the "
                 "others stop working in flows).").classes("text-xs opacity-60")

    def _cards(self, only: str = "") -> None:
        loaded, failed, disabled, manifests = self._status()
        off = self._switches.off() if self._switches else set()
        rows = [(p, "off" if p in off else "loaded", "") for p in loaded]
        rows += [(p, "failed", reason) for p, reason in failed.items()]
        rows += [(p, "disabled", "Not in [plugins] enabled in the settings file.") for p in disabled]
        switched_off = len([p for p in loaded if p in off])
        if only:
            rows = [row for row in rows if row[0] == only]
            if not rows:
                ui.label(f"No plugin {only} here.").classes("opacity-70")
        else:
            ui.label(f"{len(loaded) - switched_off} on · {switched_off} off · {len(failed)} failed · "
                     f"{len(disabled)} not loaded").classes("opacity-80")
            if not rows:
                ui.label("No plugins found in the plugins folder.").classes("opacity-70")
        pages = {path.split("/")[2]: path for _, path, _ in self._ui.pages if path.count("/") == 2}
        with ui.element("div").classes("grid gap-4 w-full items-start"
                                       + ("" if only else " sm:grid-cols-2 lg:grid-cols-3")):
            for plugin_id, status, detail in rows:
                manifest = manifests.get(plugin_id)
                with ui.card().classes("w-full"):
                    with ui.row().classes("w-full items-center no-wrap gap-2"):
                        ui.icon("extension").classes("text-xl text-primary")
                        ui.label(manifest.name if manifest else plugin_id).classes("font-semibold")
                        ui.space()
                        ui.badge(status).props(f"color={STATUS_COLOURS[status]}")
                    version = f" · version {manifest.version}" if manifest else ""
                    ui.label(f"{plugin_id}{version}").classes("text-xs opacity-60 font-mono")
                    if detail:
                        ui.label(detail).classes("text-sm break-words" + (" text-negative" if status == "failed" else ""))
                    if status in ("loaded", "off") and self._switches:
                        ui.switch("On", value=status == "loaded",
                                  on_change=lambda e, p=plugin_id: self._switch(p, e.value)) \
                            .tooltip("Off: everything of the plugin stops. Its boxes don't run (also in "
                                     "your flows: they stop there and say why), its triggers start nothing, "
                                     "its tool, cards, page and connection are gone. Your flows keep its "
                                     "boxes: switch it on and they work again")
                        if status == "off":
                            ui.label("Off: nothing of it runs, not even its boxes in your flows. They stay in "
                                     "the flows and work again once it is on.").classes("text-xs opacity-70")
                    if status in ("loaded", "off"):
                        self._keys(plugin_id)
                    if status == "loaded" and plugin_id in pages:
                        ui.button("Open", icon="open_in_new").props(f"no-caps flat dense href={pages[plugin_id]}")

    def _keys(self, plugin_id: str) -> None:
        """A field per key the plugin needs (ctx.secret, a web box's {secret.name}): typed here, never shown."""
        for owner, label, hint, file in self._ui.secrets:
            if owner == plugin_id:
                SecretInput(file, label, saved="Saved. Its boxes use it from now on.")
                if hint:
                    ui.label(hint).classes("text-xs opacity-70")

    def _new(self) -> None:
        """A window: the new plugin's name and kind; Create makes its folder from the template."""
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full"):
            ui.label("New plugin").classes("text-lg font-semibold")
            name = ui.input("Name", placeholder="My weather").props("outlined dense autofocus").classes("w-full")
            kind = ui.radio({True: "With code (Python): boxes, triggers, a connection, tools, ...",
                             False: "Without code: boxes that call a web API (JSON files)"},
                            value=True).classes("text-sm")

            def create() -> None:
                try:
                    folder = self._template.make(name.value or "", kind.value)
                except (ValueError, OSError) as e:
                    ui.notify(str(e), type="warning")
                    return
                dialog.close()
                ui.notify(f"Made {folder}. Restart the toolbox (Settings → Restart) to load it.",
                          type="positive", multi_line=True, timeout=10000)

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("no-caps flat")
                ui.button("Create", icon="add", on_click=create).props("no-caps unelevated")
            ui.label("It is made in the plugins folder with a first box that works. How to go on: "
                     "docs/PLUGINS.md.").classes("text-xs opacity-70")
        dialog.open()

    async def _switch(self, plugin_id: str, on: bool) -> None:
        if self._power:
            await self._power.switch(plugin_id, on)
        else:
            self._switches.switch(plugin_id, on)
        ui.navigate.reload()  # the side list too: a plugin that is off is not in it


def _owner(path: str) -> str:
    """The plugin id in a plugin page's address (/plugins/<id>/...)."""
    parts = path.split("/")
    return parts[2] if len(parts) > 2 else ""
