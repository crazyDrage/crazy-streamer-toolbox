from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.connections.inbox_address import DEFAULT_TYPE, inbox_address
from streamer_toolbox.core.interfaces.message_inbox import MessageInbox

CopyText = tuple[str, str, Callable[[str], str]]  # a button's text, its icon, the text it copies for a type


class InboxAddressPanel:
    """The addresses a program connects to so its messages come in (MessageInbox), on that connection's tab:
    every type that connected once or was added (live or not, Copy address and the program's own Copy buttons,
    Remove), a field for a new type with its address and Add, and New key. A type is listed once it has
    connected (his 11-21) or he added it (his 11-22: VNyan only connects when it sends; Warudo too)."""

    def __init__(self, connection_id: str, program: str, port: int, inbox: MessageInbox, key: Callable[[], str],
                 new_key: Callable[[], str], more: list[CopyText] | None = None) -> None:
        self._connection_id = connection_id
        self._program = program  # its name in the texts (Warudo, VNyan)
        self._port = port
        self._inbox = inbox
        self._key = key
        self._new_key = new_key
        self._more = more or []  # more Copy buttons for the typed type (Warudo: asset, blueprint)
        self._refresh: Callable[[], None] = lambda: None  # set by build()

    def address(self, kind: str, key: str) -> str:
        return inbox_address(self._port, self._connection_id, kind, key)

    def build(self) -> None:
        ui.label("Types").classes("text-sm font-semibold")
        seen = {"types": self._types()}

        @ui.refreshable
        def type_list() -> None:
            known, live = seen["types"]
            if not known:
                ui.label(f"None yet. Add a type below (e.g. {DEFAULT_TYPE}), or copy its address into "
                         f"{self._program}: it also shows here once it has connected.").classes("text-sm opacity-70")
            for kind in known:
                with ui.row().classes("items-center gap-2 w-full no-wrap"):
                    ui.label(kind).classes("text-sm font-mono flex-1 break-all")
                    if kind in live:
                        ui.badge("live", color="positive")
                    else:
                        ui.badge("not connected", color="grey")
                    ui.button(icon="content_copy", on_click=lambda k=kind: self._copy(k)) \
                        .props("flat dense round").tooltip("Copy its address (with the key)")
                    for text, icon, make in self._more:
                        ui.button(icon=icon, on_click=lambda k=kind, make=make, text=text: self._copy_text(
                            make(k), text)).props("flat dense round").tooltip(f"{text} for {kind}")
                    if kind in live:  # a live one can't be removed: its place stays, so the buttons line up
                        ui.element("div").classes("w-8 shrink-0")
                    else:
                        ui.button(icon="delete", on_click=lambda k=kind: self._remove(k)) \
                            .props("flat dense round").tooltip("Remove it from the list (it comes back when it "
                                                               "connects again)")

        type_list()

        def refresh_if_changed() -> None:
            now = self._types()
            if now != seen["types"]:
                seen["types"] = now
                type_list.refresh()

        ui.timer(2.0, refresh_if_changed)
        self._refresh = refresh_if_changed

        ui.label("Another type").classes("text-sm font-semibold mt-2")
        kind = ui.input("Type", value=DEFAULT_TYPE).classes("w-full")
        ui.label("Any word you like, e.g. camera or wave.").classes("text-xs opacity-60 -mt-2")
        shown = ui.label().classes("text-sm font-mono break-all")

        def show() -> None:
            shown.set_text(self.address(kind.value or "", "•" * 8))

        kind.on_value_change(lambda _: show())
        show()

        with ui.row().classes("gap-2"):
            ui.button("Add", icon="add", on_click=lambda: self._add(kind.value or "")) \
                .props("no-caps unelevated").tooltip("Lists this type above, before it ever connected")
            ui.button("Copy address", icon="content_copy", on_click=lambda: self._copy(kind.value or "")) \
                .props("no-caps outline")
            for text, icon, make in self._more:
                ui.button(text, icon=icon, on_click=lambda make=make, text=text: self._copy_text(
                    make(kind.value or DEFAULT_TYPE), text)).props("no-caps outline")
            ui.button("New key", icon="key", on_click=self._renew).props("no-caps outline")

    def _types(self) -> tuple[list[str], list[str]]:
        live = self._inbox.live_types()
        known = sorted(set(self._inbox.known_types()) | set(live), key=str.casefold)
        return known, live

    def _copy(self, kind: str) -> None:
        ui.clipboard.write(self.address(kind, self._key()))
        ui.notify("Address copied (with its key)", type="positive")

    @staticmethod
    def _copy_text(text: str, what: str) -> None:
        ui.clipboard.write(text)
        ui.notify(f"{what.removeprefix('Copy ').capitalize()} copied: paste it into the program", type="positive")

    def _add(self, kind: str) -> None:
        kind = kind.strip() or DEFAULT_TYPE
        self._inbox.add_type(kind)
        self._refresh()
        ui.notify(f"{kind} added: copy its address into {self._program}", type="positive")

    def _remove(self, kind: str) -> None:
        self._inbox.forget(kind)
        self._refresh()
        ui.notify(f"{kind} removed from the list")

    async def _renew(self) -> None:
        with ui.dialog() as dialog, ui.card():
            ui.label("Make a new key?").classes("font-semibold")
            ui.label("Every address you copied before stops working. Paste the new one into each program "
                     "again.").classes("text-sm")
            with ui.row().classes("gap-2"):
                ui.button("New key", on_click=lambda: dialog.submit(True)).props("no-caps unelevated")
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("no-caps flat")
        if await dialog:
            self._new_key()
            ui.notify("New key made: copy the addresses again", type="positive")
