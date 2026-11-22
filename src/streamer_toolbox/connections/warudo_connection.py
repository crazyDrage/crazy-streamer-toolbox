from pathlib import Path
from typing import Any

from nicegui import ui

from streamer_toolbox.connections.warudo.warudo_actions import WarudoActions
from streamer_toolbox.connections.warudo.warudo_copy_texts import WarudoCopyTexts
from streamer_toolbox.connections.websocket.socket_inbox import SocketInbox
from streamer_toolbox.connections.websocket.socket_message_sender import SocketMessageSender
from streamer_toolbox.connections.websocket.visit_connection import VisitConnection
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.inbox_address import inbox_address
from streamer_toolbox.core.connections.inbox_types import InboxTypes
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.interfaces.message_inbox import MessageInbox
from streamer_toolbox.gui.components.inbox_address_panel import InboxAddressPanel
from streamer_toolbox.gui.components.outside_link import outside_link

DOCS = "https://docs.warudo.app/docs/blueprints/overview"
PLUGIN = "https://steamcommunity.com/sharedfiles/filedetails/?id=3226193710"  # "Send Websocket" by veasu


class WarudoConnection(VisitConnection):
    """Warudo (3D VTubing program): named actions and raw texts into its blueprints, over its websocket on port
    19190; nothing is kept open, each message is its own short visit (VisitConnection). Its boxes are in
    WarudoActions. Tried 11-21: {"action": "test_trigger"} ran an On WebSocket Action node (its own hint shows
    that shape).

    The other way, Warudo → toolbox, goes through the free plugin "Send Websocket" (by veasu, Steam Workshop
    3226193710): its "Send Websocket Asset" connects to the toolbox's address and its "Send Websocket Message"
    node sends a text there (SocketInbox, the trigger "Message from Warudo"). Tried 11-21: a whole camera came
    as a JSON text packed twice, because his node had "JSON Stringify Output" on for a value that was JSON text
    already (his 11-22); the trigger gives the text as it came. Off until switched on."""

    id = "warudo"
    title = "Warudo"
    icon = "view_in_ar"

    def __init__(self, settings: dict[str, Any], sender: SocketMessageSender | None = None,
                 events: EventBus | None = None, in_key: SecretFile | None = None, port: int = 8850,
                 in_types: InboxTypes | None = None, again_after: float = 0.5) -> None:
        super().__init__({"url": "ws://localhost:19190"}, settings, sender, again_after)
        self._port = port  # the toolbox's own, for the address Warudo connects to
        self._inbox = SocketInbox(self.id, self.title, in_key, events, lambda: bool(self._settings["enabled"]),
                                  in_types) \
            if events is not None and in_key is not None and in_types is not None else None

    def inbox(self) -> MessageInbox | None:
        return self._inbox

    def in_address(self, kind: str) -> str:
        """The address (with its key) Warudo's asset of this type connects to."""
        if self._inbox is None:
            raise NotConnectedError("this toolbox takes no messages from Warudo")
        return inbox_address(self._port, self.id, kind, self._inbox.key())

    def default_flows(self) -> Path:
        """Connect input: the asset connects again once the toolbox finds Warudo (his idea, 11-21)."""
        return Path(__file__).parent / "warudo" / "default_flows.flows.toml"

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Websocket address", hint="Warudo listens on port 19190 while it runs")]

    def add_gui_settings(self) -> None:
        ui.label("Toolbox → Warudo").classes("font-semibold")
        ui.label('What Warudo does is built in Warudo: start a blueprint with an "On WebSocket Action" node and '
                 'give it an Action. A flow\'s "Send action to Warudo" box with the same name runs it. '
                 'An "On WebSocket Raw Message" node runs on any text: the "Send raw message to Warudo" box.') \
            .classes("text-sm opacity-80")
        outside_link("Warudo's handbook: blueprints", DOCS).classes("text-sm")
        if self._inbox is None:
            return
        ui.separator()
        ui.label("Warudo → toolbox").classes("font-semibold")
        texts = WarudoCopyTexts()
        InboxAddressPanel(self.id, self.title, self._port, self._inbox, self._inbox.key, self._inbox.new_key,
                          [("Copy asset", "inventory_2", lambda kind: texts.asset(kind, self.in_address(kind))),
                           ("Copy blueprint", "account_tree", texts.blueprint)]).build()
        ui.label("How to set it up in Warudo").classes("text-sm font-semibold mt-2")
        # his mini guide (11-21, temp/notes.txt)
        for step in ('1. Add the Steam Workshop item "Send Websocket" (link below).',
                     "2. Add the connection: Assets → the + at the bottom (Add Asset) → Websocket → "
                     '"Send Websocket Asset".',
                     "   Optional: rename the asset with Rename at the bottom (next to + − Duplicate).",
                     "3. Copy address above and paste it into the asset's Websocket URL field.",
                     "   Or: Copy asset above and paste it into Warudo as a new asset (it has the address).",
                     '4. In a blueprint: search and add "Send Websocket Message". Set the asset under '
                     "Websocket Asset, and write what to send under Templated Message.",
                     '5. In Flows: the trigger "Message from Warudo". Pick the type, or ALL. Its values: type '
                     'and text (as it came). For an object: the box "JSON text to value". In Warudo, "JSON '
                     'Stringify Output" on Yes packs the message as JSON text, so leave it on No for a value that '
                     "is JSON already.",
                     "Add a type above to list it (it also shows once it has connected). Another type = another "
                     "asset with its own address; they can all be connected at once.",
                     "Connects again after the toolbox was closed: Copy blueprint above, paste it into Warudo, and "
                     'switch on the default flow "Warudo - default - connect input" (Add default flows below). '
                     "When the toolbox finds Warudo, it sends the address and the blueprint sets it on the asset."):
            ui.label(step.strip()).classes("text-sm" + (" pl-4" if step.startswith("   ") else ""))
        outside_link('The Workshop item "Send Websocket"', PLUGIN).classes("text-sm")

    def add_actions(self, actions: ActionRegistry) -> None:
        if self._inbox is None:
            WarudoActions(self._send_text).add_to(actions)
        else:
            WarudoActions(self._send_text, self.in_address, self._inbox.known_types).add_to(actions)
