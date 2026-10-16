from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.gui.services.ui_registry import UiRegistry
from streamer_toolbox.plugins.plugin_manifest import PluginManifest
from streamer_toolbox.plugins.plugin_switches import PluginSwitches

# loaded ids, failed id -> reason, disabled ids, folder manifests by id
PluginStatus = Callable[[], tuple[list[str], dict[str, str], list[str], dict[str, PluginManifest]]]
STATUS_COLOURS = {"loaded": "positive", "off": "grey", "failed": "negative", "disabled": "grey"}


class PluginsPage:
    """One card per plugin found: loaded, failed (with the reason) or disabled by the enable list. A loaded
    one has a switch: off = its boxes and triggers are no longer offered for adding (PluginSwitches); what
    flows already use stays and keeps working.

    The side list (side_items, his wish of 2026-10-14: "sub items on the side list") has a row per plugin,
    /plugins?show=<id>: its card and its panels (the "live" and "settings" ones; they are on neither Live nor
    Settings any more), and below it a row per page the plugin added."""

    def __init__(self, status: PluginStatus, ui_registry: UiRegistry, switches: PluginSwitches | None = None) -> None:
        self._status = status
        self._ui = ui_registry
        self._switches = switches

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
            if owner == plugin_id and section in ("live", "settings"):
                with ui.card().classes("w-full"):
                    ui.label(title).classes("text-lg font-semibold")
                    builder()

    @ui.refreshable_method
    def _all(self) -> None:
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
                            .tooltip("Off: its boxes and triggers are no longer offered in Add box and Add "
                                     "trigger. The ones your flows already use stay and keep working until "
                                     "you delete them")
                        if status == "off":
                            ui.label("Off: not offered for adding. What your flows already use keeps working.") \
                                .classes("text-xs opacity-70")
                    if status in ("loaded", "off") and plugin_id in pages:
                        ui.button("Open", icon="open_in_new").props(f"no-caps flat dense href={pages[plugin_id]}")

    def _switch(self, plugin_id: str, on: bool) -> None:
        self._switches.switch(plugin_id, on)
        ui.navigate.reload()  # the side list too: a plugin that is off is not in it


def _owner(path: str) -> str:
    """The plugin id in a plugin page's address (/plugins/<id>/...)."""
    parts = path.split("/")
    return parts[2] if len(parts) > 2 else ""
