import secrets
from pathlib import Path

from nicegui import ui

from streamer_toolbox.core.config.toolbox_config import ToolboxConfig
from streamer_toolbox.core.connections.connection_manager import ConnectionManager
from streamer_toolbox.core.interfaces.connection import Connection
from streamer_toolbox.core.testing.test_item import CONNECTION
from streamer_toolbox.core.testing.test_view import TestView
from streamer_toolbox.gui.components.connection_panel import STATE_LOOK, ConnectionPanel
from streamer_toolbox.gui.services.ui_registry import UiRegistry

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
TOOLBOX = "toolbox"  # ?show=toolbox: the toolbox's own API and callers


class ConnectionsPage:
    """Everything that talks to the toolbox or that it talks to. /connections is the overview: one card per
    Connection (OBS, SAMMI, Mix It Up, ...) with its state, and the toolbox's own API. /connections?show=<id> is
    one connection's settings (the left menu lists them under Connections), ?show=toolbox the API and callers.
    Connections are set up right here; the API and callers are changed in config/toolbox.toml (restart needed).
    The overview and the menu leave out the connections his checks hide (`view`, Settings → What you see): such
    a connection stays as it is (connected or not), and its address still opens it."""

    def __init__(self, config: ToolboxConfig, config_path: Path, ui_registry: UiRegistry,
                 connections: ConnectionManager, view: TestView | None = None) -> None:
        self._config = config
        self._path = config_path
        self._ui = ui_registry
        self._connections = connections
        self._view = view

    def shown(self) -> list[Connection]:
        """The connections the overview and the side menu list now."""
        return [connection for connection in self._connections.all()
                if self._view is None or self._view.shows_key(f"{CONNECTION}:{connection.id}")]

    def build(self) -> None:
        show = ui.context.client.request.query_params.get("show", "")
        connection = next((c for c in self._connections.all() if c.id == show), None)
        if connection is not None:
            self._back()
            ConnectionPanel(connection, self._connections).build()
        elif show == TOOLBOX:
            self._back()
            self._toolbox()
        else:
            self._overview()

    @staticmethod
    def _back() -> None:
        ui.link("← All connections", "/connections").classes("text-sm")

    def _overview(self) -> None:
        shown = self.shown()
        hidden = len(self._connections.all()) - len(shown)
        if hidden:
            ui.label(f"{hidden} connections hidden: {self._view.why()}. They stay as they are (connected or "
                     "not). Change it in Settings → What you see").classes("text-xs opacity-60")
        with ui.element("div").classes("grid gap-3 w-full sm:grid-cols-2 xl:grid-cols-3 items-stretch"):
            self._tile("lan", "Toolbox", TOOLBOX, "Its own API, and who may call it")
            for connection in shown:
                self._tile(connection.icon, connection.title, connection.id)

    def _tile(self, icon: str, title: str, show: str, note: str = "") -> None:
        """One card of the overview: a click opens that connection; its state stays current."""
        connection = next((c for c in self._connections.all() if c.id == show), None)
        with ui.link(target=f"/connections?show={show}").classes("no-underline text-inherit"), \
                ui.card().classes("w-full h-full gap-1 cursor-pointer hover:bg-gray-500/10"):
            with ui.row().classes("items-center no-wrap gap-2 w-full"):
                ui.icon(icon).classes("text-2xl text-primary")
                ui.label(title).classes("text-lg font-semibold flex-1")
                if connection is not None:
                    badge = ui.badge()
            detail = ui.label(note).classes("text-xs opacity-70 break-all")
            if connection is None:
                return

            def draw() -> None:
                status = connection.status
                text, colour = STATE_LOOK[status.state]
                badge.set_text(text)
                badge.props(f"color={colour}")
                detail.set_text(status.detail or ", ".join(f"{name}: {value}" for name, value in status.facts))

            draw()
            ui.timer(2.0, draw)

    def _toolbox(self) -> None:
        with ui.element("div").classes("grid gap-4 w-full lg:grid-cols-2 items-start"):
            self._api_card()
            self._callers_card()
            for _, title, builder in self._ui.panels_for("connections"):
                with ui.card().classes("w-full"):
                    ui.label(title).classes("font-semibold")
                    builder()

    @staticmethod
    def _card_title(icon: str, title: str) -> None:
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon).classes("text-xl text-primary")
            ui.label(title).classes("text-lg font-semibold")

    @staticmethod
    def _field(name: str, value: str) -> None:
        with ui.row().classes("w-full no-wrap gap-3 text-sm"):
            ui.label(name).classes("w-28 shrink-0 opacity-70")
            ui.label(value).classes("break-all")

    def _api_card(self) -> None:
        with ui.card().classes("w-full gap-2"):
            self._card_title("lan", "Toolbox API")
            local_only = self._config.host in LOOPBACK_HOSTS
            self._field("Address", f"http://{self._config.host}:{self._config.port}")
            self._field("Reachable from", "this PC only" if local_only else "this PC and the local network")
            self._field("Settings file", str(self._path) if self._path.exists()
                        else f"{self._path.name} not created yet, using defaults")
            ui.label("Change settings in the file, then restart the toolbox.").classes("text-xs opacity-60")

    def _callers_card(self) -> None:
        with ui.card().classes("w-full gap-2"):
            self._card_title("key", "Callers and tokens")
            ui.label("Who may use the API, and which actions each one may run.").classes("text-sm opacity-80")
            for caller in self._config.callers:
                with ui.column().classes("w-full gap-1 border-t border-gray-500/30 pt-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(caller.name).classes("font-semibold")
                        if caller.local:
                            ui.badge("this PC").props("outline color=positive")
                        if caller.token:
                            ui.badge("token").props("outline color=primary")
                    if caller.token:
                        with ui.row().classes("items-center gap-1 text-sm"):
                            ui.label("Token ••••" + caller.token[-4:]).classes("font-mono")
                            ui.button("Copy", icon="content_copy",
                                      on_click=lambda t=caller.token: self._copy(t, "Token")).props("flat no-caps")
                    allowed = "everything" if "*" in caller.allow else ", ".join(caller.allow) or "nothing"
                    self._field("May run", allowed)
            ui.button("New token", icon="add", on_click=self._new_token).props("no-caps flat")

    @staticmethod
    def _copy(text: str, what: str) -> None:
        ui.clipboard.write(text)
        ui.notify(f"{what} copied", type="positive")

    def _new_token(self) -> None:
        token = secrets.token_urlsafe(32)
        snippet = f'[callers.NAME]\ntoken = "{token}"\nallow = ["hello.greet"]\n'
        with ui.dialog() as dialog, ui.card().classes("w-[32rem] max-w-full"):
            ui.label("New caller token").classes("text-lg font-semibold")
            ui.label(f"Add this to {self._path.name}, set the name and allowed actions, and restart. "
                     "Give the token only to that caller.").classes("text-sm opacity-80")
            ui.code(snippet, language="toml").classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Copy", icon="content_copy", on_click=lambda: self._copy(snippet, "Snippet")) \
                    .props("no-caps unelevated")
                ui.button("Close", on_click=dialog.close).props("no-caps flat")
        dialog.open()
