from pathlib import Path

from nicegui import app, ui

from streamer_toolbox.core.security.remote_access import RemoteAccess
from streamer_toolbox.core.security.signed_in_devices import SignedInDevices
from streamer_toolbox.core.system.toolbox_restart import ToolboxRestart
from streamer_toolbox.gui.components.app_shell import AppShell
from streamer_toolbox.gui.components.box_filter_panel import BoxFilterPanel
from streamer_toolbox.gui.components.role_loading_panel import RoleLoadingPanel
from streamer_toolbox.gui.components.test_view_panel import TestViewPanel
from streamer_toolbox.gui.services.ui_registry import UiRegistry


class SettingsPage:
    """How the toolbox looks, where its settings file is, Restart, who may open it from other devices, his own
    filters for the Add box window, what he sees by his checks (TestViewPanel), when viewer roles are loaded
    (RoleLoadingPanel), and settings panels from plugins."""

    def __init__(self, config_path: Path, ui_registry: UiRegistry, access: RemoteAccess, devices: SignedInDevices,
                 port: int, restart: ToolboxRestart | None = None,
                 box_filters: BoxFilterPanel | None = None, seen: TestViewPanel | None = None,
                 roles: RoleLoadingPanel | None = None) -> None:
        self._roles = roles
        self._path = config_path
        self._ui = ui_registry
        self._access = access
        self._devices = devices
        self._port = port
        self._restart = restart
        self._box_filters = box_filters
        self._seen = seen

    def sections(self) -> list[tuple[str, str, str]]:
        """The page's parts, for the side menu: (title, address, icon). /settings shows all of them,
        /settings?show=<part> only that one."""
        parts = [("General", "general", "tune"), ("Other devices", "devices", "devices")]
        if self._box_filters is not None:
            parts.append(("Add box filters", "boxes", "filter_list"))
        if self._seen is not None:
            parts.append(("What you see", "seen", "visibility"))
        if self._roles is not None:
            parts.append(("Viewer roles", "roles", "groups"))
        if self._ui.panels_for("settings"):
            parts.append(("Plugins", "plugins", "extension"))
        return [(title, f"/settings?show={key}", icon) for title, key, icon in parts]

    def build(self) -> None:
        show = ui.context.client.request.query_params.get("show", "")
        known = {address.rsplit("=", 1)[1] for _, address, _ in self.sections()}

        def shown(part: str) -> bool:
            return show not in known or show == part

        with ui.element("div").classes("grid gap-4 w-full items-start"
                                       + (" lg:grid-cols-2" if show not in ("devices", "boxes") else "")):
            if shown("general"):
                with ui.card().classes("w-full"):
                    ui.label("Appearance").classes("text-lg font-semibold")
                    ui.label("Theme for every screen that opens the toolbox").classes("text-sm opacity-80")
                    ui.toggle({"dark": "Dark", "light": "Light", "auto": "Like the device"}, value=AppShell.theme(),
                              on_change=lambda e: self._set_theme(e.value)).props("no-caps unelevated")
                if self._restart is not None and self._restart.available:
                    with ui.card().classes("w-full"):
                        self._restart_card()
                with ui.card().classes("w-full"):
                    ui.label("Settings file").classes("text-lg font-semibold")
                    ui.label(str(self._path)).classes("text-sm font-mono break-all")
                    if not self._path.exists():
                        ui.label(f"Not created yet. Copy {self._path.parent.name}/toolbox.example.toml to "
                                 f"{self._path.name} to change the defaults.").classes("text-sm opacity-80")
                    ui.label("Connections, callers, tokens, plugins and OBS are set there. Restart after "
                             "changes.").classes("text-xs opacity-60")
            if shown("devices"):
                with ui.card().classes("w-full"):
                    self._other_devices()
            if shown("boxes") and self._box_filters is not None:
                with ui.card().classes("w-full"):
                    self._box_filters.build()
            if shown("seen") and self._seen is not None:
                with ui.card().classes("w-full"):
                    self._seen.build()
            if shown("roles") and self._roles is not None:
                with ui.card().classes("w-full"):
                    self._roles.build()
            if shown("plugins"):
                for _, title, builder in self._ui.panels_for("settings"):
                    with ui.card().classes("w-full"):
                        ui.label(title).classes("font-semibold")
                        builder()

    def _restart_card(self) -> None:
        ui.label("Restart").classes("text-lg font-semibold")
        ui.label("Starts the toolbox again: reads new code, flows, plugins and the settings file. Open pages "
                 "(also this window) reconnect by themselves after a few seconds.").classes("text-sm opacity-80")
        with ui.dialog() as dialog, ui.card():
            ui.label("Restart the toolbox now?").classes("text-lg font-semibold")
            ui.label("Flows that are running right now stop. Timers and triggers start again with it.") \
                .classes("text-sm")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
                ui.button("Restart", icon="restart_alt", on_click=lambda: self._do_restart(dialog)) \
                    .props("unelevated no-caps color=warning")
        ui.button("Restart the toolbox", icon="restart_alt", on_click=dialog.open).props("outline no-caps")

    def _do_restart(self, dialog: ui.dialog) -> None:
        dialog.close()
        ui.notify("Restarting: this page comes back by itself in a few seconds", type="ongoing", timeout=8000)
        ui.timer(0.5, self._restart.request, once=True)  # let the message reach the page first

    @ui.refreshable_method
    def _other_devices(self) -> None:
        access = self._access
        request = getattr(ui.context.client, "request", None)
        remote = not RemoteAccess.is_this_pc(request.client.host if request and request.client else None)
        ui.label("Other devices").classes("text-lg font-semibold")
        ui.label("Open the toolbox on your phone, tablet or laptop at home, with a password. This PC never needs "
                 "it.").classes("text-sm opacity-80")
        if access.open and not access.restart_needed:
            ui.label(f"On. Open http://{RemoteAccess.lan_address()}:{self._port} on the other device.") \
                .classes("text-sm text-positive font-medium")
        elif access.restart_needed:
            ui.label("Restart the toolbox to apply this.").classes("text-sm text-warning font-medium")
            if access.open:
                ui.label("The first time, Windows asks whether Python may use the network: pick Private "
                         "networks. Do it when you're not live, the popup could show on stream.") \
                    .classes("text-xs opacity-80")
        else:
            ui.label("Off: only this PC.").classes("text-sm opacity-80")

        with ui.row().classes("items-end no-wrap gap-2 w-full"):
            first = ui.input("New password", password=True, password_toggle_button=True) \
                .props("dense outlined").classes("flex-1")
            again = ui.input("Again", password=True).props("dense outlined").classes("flex-1")

            def save_password() -> None:
                if len(first.value or "") < 8:
                    ui.notify("Use at least 8 characters", type="warning")
                elif first.value != again.value:
                    ui.notify("The two passwords are not the same", type="warning")
                else:
                    access.set_password(first.value)
                    ui.notify("Password saved. Other devices sign in again.", type="positive")
                    self._other_devices.refresh()

            ui.button("Save", icon="key", on_click=save_password).props("no-caps unelevated")
        ui.label("A password is set." if access.has_password else "No password yet.").classes("text-xs opacity-70")

        def switch(e) -> None:
            try:
                access.set_open(e.value)
            except ValueError as error:
                ui.notify(str(error), type="warning")
            self._other_devices.refresh()

        ui.switch("Let other devices on my network in", value=access.open, on_change=switch) \
            .props("" if access.has_password or access.open else "disable")
        ui.label("Only for your home network: the password goes over it unencrypted (plain http). From outside "
                 "your home, use a VPN, never a router port forward.").classes("text-xs opacity-60")
        if remote:
            browser = request.session.get("id") if "session" in request.scope else None
            ui.button("Sign out this device", icon="logout", on_click=lambda: self._sign_out(browser)) \
                .props("no-caps flat dense")

    def _sign_out(self, browser: str | None) -> None:
        self._devices.remove(browser)
        ui.navigate.to("/login")

    @staticmethod
    def _set_theme(theme: str) -> None:
        app.storage.general["theme"] = theme
        ui.navigate.reload()
