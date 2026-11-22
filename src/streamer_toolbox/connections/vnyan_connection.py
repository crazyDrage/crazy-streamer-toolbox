from typing import Any

from nicegui import ui

from streamer_toolbox.connections.vnyan.vnyan_actions import VNyanActions
from streamer_toolbox.connections.vnyan.vnyan_copy_texts import VNyanCopyTexts
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

DOCS = "https://github.com/Suvidriel/VNyanDoc/wiki"


class VNyanConnection(VisitConnection):
    """VNyan (3D VTubing program): named messages and data into its node graph, over its websocket receiver
    (Settings → Misc → WebSockets, "Start Receiver"). Nothing is kept open, each message is its own short visit
    (VisitConnection). Its boxes are in VNyanActions. (Its web API on 8069 is no longer used: 11-22, his
    "outdated now", Send data does it over the websocket.)

    The other way, VNyan → toolbox: its "WebSocket Message" node sends a text to the toolbox's address
    (SocketInbox, the trigger "Message from VNyan"). Tried with him 11-22 (temp/recordings/vnyan/README.md):
    one visit per message; "localhost" goes to ::1, so the address is 127.0.0.1. Off until switched on."""

    id = "vnyan"
    title = "VNyan"
    icon = "pets"

    def __init__(self, settings: dict[str, Any], sender: SocketMessageSender | None = None,
                 again_after: float = 0.5, events: EventBus | None = None, in_key: SecretFile | None = None,
                 port: int = 8850, in_types: InboxTypes | None = None) -> None:
        super().__init__({"url": "ws://127.0.0.1:8000/vnyan"}, settings, sender, again_after)
        self._port = port  # the toolbox's own, for the address VNyan sends to
        self._inbox = None
        if events is not None and in_key is not None and in_types is not None:
            self._inbox = SocketInbox(self.id, self.title, in_key, events,
                                      lambda: bool(self._settings["enabled"]), in_types)

    def inbox(self) -> MessageInbox | None:
        return self._inbox

    def in_address(self, kind: str) -> str:
        """The address (with its key) VNyan's WebSocket Message node sends messages of this type to."""
        if self._inbox is None:
            raise NotConnectedError("this toolbox takes no messages from VNyan")
        return inbox_address(self._port, self.id, kind, self._inbox.key())

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Websocket address",
                             hint="VNyan → Settings → Misc → WebSockets: Start Receiver on; the port is there")]

    def add_gui_settings(self) -> None:
        ui.label("Toolbox → VNyan").classes("font-semibold")
        ui.label('What VNyan does with a message is built in VNyan: add a "WebSocket Command" node to a node '
                 'graph and give it a Command Text. A flow\'s "Send message to VNyan" box with the same text '
                 "runs it.").classes("text-sm opacity-80")
        # tried with him 11-22 (temp/recordings/vnyan/README.md)
        for line in ("Send message: the node whose Command Text the message starts with runs. Its Value is the "
                     "number after it (whole numbers only, else 0); its Message is the whole line.",
                     "Send data: for a WebSocket Command node with an EMPTY Command Text (it runs on every "
                     "message). Its Data gets the values; read each one with a Dictionary Values node by its "
                     "name. Values inside values arrive as text.",
                     'Both boxes have a "Copy VNyan block" button: the nodes to paste into a VNyan node graph.'):
            ui.label(line).classes("text-xs opacity-60")
        outside_link("VNyan's documentation", DOCS).classes("text-sm")
        if self._inbox is None:
            return
        ui.separator()
        ui.label("VNyan → toolbox").classes("font-semibold")
        texts = VNyanCopyTexts()
        InboxAddressPanel(self.id, self.title, self._port, self._inbox, self._inbox.key, self._inbox.new_key,
                          [("Copy VNyan block", "account_tree",
                            lambda kind: texts.send_block(self.in_address(kind)))]).build()
        ui.label("How to set it up in VNyan").classes("text-sm font-semibold mt-2")
        for step in ('1. Copy VNyan block above and paste it into a node graph: a "WebSocket Message" node with '
                     "the address in its Server Address.",
                     "   Or: add that node yourself, then Copy address above and paste it into its Server Address.",
                     "2. Write what to send into its Message (or wire a text into it).",
                     '3. In Flows: the trigger "Message from VNyan". Pick the type, or ALL. Its values: type '
                     'and text (as it came). For an object: the box "JSON text to value".',
                     "Add a type above to list it (it also shows once it has sent something). Another type = "
                     "the same address with another word in it."):
            ui.label(step.strip()).classes("text-sm" + (" pl-4" if step.startswith("   ") else ""))

    def add_actions(self, actions: ActionRegistry) -> None:
        VNyanActions(self._send_text).add_to(actions)

    def _reason(self, e: BaseException) -> str:
        if isinstance(e, (OSError, TimeoutError)):
            return "can't reach VNyan: is it running, with Settings → Misc → WebSockets → Start Receiver on?"
        return super()._reason(e)
