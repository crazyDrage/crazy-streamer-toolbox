from nicegui import ui

from streamer_toolbox.core.interfaces.connection import Connection
from streamer_toolbox.core.connections.connection_manager import ConnectionManager
from streamer_toolbox.core.connections.connection_state import ConnectionState

STATE_LOOK = {  # badge text, Quasar colour
    ConnectionState.OFF: ("off", "grey"),
    ConnectionState.CONNECTING: ("connecting…", "warning"),
    ConnectionState.CONNECTED: ("connected", "positive"),
    ConnectionState.ERROR: ("not connected", "negative"),
}


class ConnectionPanel:
    """The tab content for any Connection: status, on/off, its fields, Connect, then its own extra settings."""

    def __init__(self, connection: Connection, manager: ConnectionManager) -> None:
        self._connection = connection
        self._manager = manager

    def build(self) -> None:
        connection = self._connection
        with ui.card().classes("w-full max-w-2xl gap-3"):
            with ui.row().classes("items-center gap-2 w-full"):
                ui.icon(connection.icon).classes("text-2xl text-primary")
                ui.label(connection.title).classes("text-lg font-semibold")
                ui.space()
                badge = ui.badge()

            @ui.refreshable
            def status_block() -> None:
                status = connection.status
                text, colour = STATE_LOOK[status.state]
                badge.set_text(text)
                badge.props(f"color={colour}")
                if status.detail:
                    ui.label(status.detail).classes("text-sm text-negative break-all")
                for name, value in status.facts:
                    with ui.row().classes("w-full no-wrap gap-3 text-sm"):
                        ui.label(name).classes("w-36 shrink-0 opacity-70")
                        ui.label(value).classes("break-all")

            status_block()
            shown = {"status": connection.status}

            def refresh_if_changed() -> None:
                if shown["status"] != connection.status:
                    shown["status"] = connection.status
                    status_block.refresh()

            ui.timer(1.0, refresh_if_changed)

            switch = ui.switch("On (connects when the toolbox starts)", value=connection.settings["enabled"],
                      on_change=lambda e: self._set_enabled(e.value))
            inputs = {}
            saved = connection.settings
            for field in connection.fields():
                if field.secret:
                    inputs[field.key] = ui.input(field.label, password=True, password_toggle_button=True,
                                                 placeholder="saved · leave empty to keep" if saved.get(field.key)
                                                 else "").classes("w-full")
                    if saved.get(field.key):
                        with ui.row().classes("items-center gap-1 text-xs text-positive -mt-2"):
                            ui.icon("check")
                            ui.label(f"{field.label} saved")
                else:
                    inputs[field.key] = ui.input(field.label, value=str(saved.get(field.key, ""))).classes("w-full")
                if field.hint:
                    ui.label(field.hint).classes("text-xs opacity-60 -mt-2")

            async def connect() -> None:
                button.props("loading")
                typed = {key: str(element.value if element.value is not None else "").strip()
                         for key, element in inputs.items()}  # a default may be a number
                status = await self._manager.connect(connection.id, typed)
                button.props(remove="loading")
                if status.ok:
                    switch.value = True  # Connect switches it on; _set_enabled sees nothing to do
                    for field in connection.fields():
                        if field.secret:
                            inputs[field.key].value = ""
                    ui.notify(f"{connection.title} connected and saved", type="positive")
                else:
                    ui.notify(f"{connection.title}: {status.detail}. Nothing was saved.", type="negative",
                              multi_line=True)

            with ui.row().classes("gap-2"):
                button = ui.button("Connect", icon="cable", on_click=connect).props("no-caps unelevated")
            ui.label("Connect tests what you typed first. Only if that works is it saved and used, no restart "
                     "needed.").classes("text-xs opacity-60")
            connection.add_gui_settings()

    async def _set_enabled(self, enabled: bool) -> None:
        if enabled == self._connection.settings["enabled"]:
            return
        await self._manager.set_enabled(self._connection.id, enabled)
        ui.notify(f"{self._connection.title} {'on' if enabled else 'off'}")
