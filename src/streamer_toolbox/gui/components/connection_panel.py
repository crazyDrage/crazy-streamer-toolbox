import re
from dataclasses import replace
from urllib.parse import quote

from nicegui import ui

from streamer_toolbox.core.event_types.event_flows import EventFlows
from streamer_toolbox.core.flows.default_flows import DefaultFlows
from streamer_toolbox.core.flows.flow_pack import FlowPack
from streamer_toolbox.gui.components.default_flows_dialog import DefaultFlowsDialog
from streamer_toolbox.core.interfaces.connection import Connection
from streamer_toolbox.core.connections.connection_manager import ConnectionManager
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus

STATE_LOOK = {  # badge text, Quasar colour
    ConnectionState.OFF: ("off", "grey"),
    ConnectionState.CONNECTING: ("connecting…", "warning"),
    ConnectionState.CONNECTED: ("connected", "positive"),
    ConnectionState.ERROR: ("not connected", "negative"),
}
PLAIN_CONNECTING = ("", "connecting")  # a retry with nothing new to say
COUNTDOWN = re.compile(r"trying again in \d+ s")  # 2 s, 4 s, 8 s...: the log keeps the seconds


def text_to_show(shown: ConnectionStatus, new: ConnectionStatus) -> ConnectionStatus:
    """The status whose text the tab shows. A plain retry keeps the text already there, and a retry's countdown
    shows as "trying again", so the tab doesn't shrink and grow with every try (his 11-20 and 11-21); only the
    badge says it's connecting."""
    if new.state is ConnectionState.CONNECTING and new.detail in PLAIN_CONNECTING and shown.detail:
        return shown
    return replace(new, detail=COUNTDOWN.sub("trying again", new.detail))


class ConnectionPanel:
    """The tab content for any Connection: status, on/off, its fields, Connect, its own extra settings, then
    "Add default flows" when it has some (his round 66)."""

    def __init__(self, connection: Connection, manager: ConnectionManager,
                 default_flows: DefaultFlows | None = None, event_flows: EventFlows | None = None) -> None:
        self._connection = connection
        self._manager = manager
        self._default_flows = default_flows
        self._event_flows = event_flows  # its events' own flows come with the default flows (his 11-14)

    def build(self) -> None:
        connection = self._connection
        with ui.card().classes("w-full max-w-2xl gap-3"):
            with ui.row().classes("items-center gap-2 w-full"):
                ui.icon(connection.icon).classes("text-2xl text-primary")
                ui.label(connection.title).classes("text-lg font-semibold")
                ui.space()
                badge = ui.badge()

            def show_badge(status: ConnectionStatus) -> None:
                text, colour = STATE_LOOK[status.state]
                badge.set_text(text)
                badge.props(f"color={colour}")

            shown = {"status": connection.status, "text": text_to_show(connection.status, connection.status)}

            @ui.refreshable
            def status_block() -> None:
                status = shown["text"]
                if status.detail:
                    ui.label(status.detail).classes("text-sm text-negative break-all")
                for name, value in status.facts:
                    with ui.row().classes("w-full no-wrap gap-3 text-sm"):
                        ui.label(name).classes("w-36 shrink-0 opacity-70")
                        ui.label(value).classes("break-all")

            show_badge(connection.status)
            status_block()

            def refresh_if_changed() -> None:
                status = connection.status
                if shown["status"] == status:
                    return
                shown["status"] = status
                show_badge(status)
                text = text_to_show(shown["text"], status)
                if text != shown["text"]:
                    shown["text"] = text
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
            self._default_flows_part()

    def _default_flows_part(self) -> None:
        file = self._connection.default_flows()
        if self._default_flows is None or file is None or not file.is_file():
            return
        pack = FlowPack.from_text(file.read_text(encoding="utf-8"))
        ui.separator()
        ui.label("Default flows").classes("font-semibold")
        ui.label(f"Ready-made flows for {self._connection.title}: "
                 + ", ".join(f.label for f in pack.flows) + ".").classes("text-sm")
        ui.label(f'You pick which ones. They go into the folder "{pack.folder}", switched off: switch on the ones '
                 "you want in Flows.").classes("text-xs opacity-60")

        async def add() -> None:  # always the window: one there already can be updated (his 11-14)
            if await DefaultFlowsDialog(self._default_flows, file, self._event_flows,
                                        self._connection.event_types()).ask_and_add():
                link.set_visibility(True)

        with ui.row().classes("items-center gap-3"):
            ui.button("Add default flows", icon="playlist_add", on_click=add).props("no-caps outline")
            link = ui.link(f"Open {pack.folder}", f"/flows?show={quote(pack.folder)}").classes("text-sm")
            link.set_visibility(False)

    async def _set_enabled(self, enabled: bool) -> None:
        if enabled == self._connection.settings["enabled"]:
            return
        await self._manager.set_enabled(self._connection.id, enabled)
        ui.notify(f"{self._connection.title} {'on' if enabled else 'off'}")
