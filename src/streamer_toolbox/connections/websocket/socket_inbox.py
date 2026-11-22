import hmac
import secrets
from collections import Counter
from collections.abc import Callable

from streamer_toolbox.core.connections.inbox_types import InboxTypes
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.interfaces.message_inbox import MessageInbox


class SocketInbox(MessageInbox):
    """Messages FROM a program that connects to the toolbox's address (Warudo's "Send Websocket" plugin, his
    round 95; VNyan's "WebSocket Message" node, 11-22). One per connection.

    Each message becomes the event `<connection id>.message`: type (from the address) and text, exactly as it
    came. Nothing is read into it (his 11-22: no `value` read as JSON; a flow that wants an object uses JSON text
    to value, and Warudo's "JSON Stringify Output" decides whether Warudo packs it). The key is the toolbox's
    own, made at the first look, kept in the connection's secret file (config/secrets/<id>_in_key.txt)."""

    def __init__(self, connection_id: str, title: str, key: SecretFile, events: EventBus,
                 enabled: Callable[[], bool], types: InboxTypes) -> None:
        self._id = connection_id
        self._title = title
        self._key = key
        self._types = types
        self._events = events
        self._enabled = enabled
        self._open: Counter[str] = Counter()

    @property
    def event(self) -> str:
        return f"{self._id}.message"

    def key(self) -> str:
        """The key the address carries; made the first time it is asked for."""
        key = self._key.read_or_empty()
        if not key:
            key = self.new_key()
        return key

    def new_key(self) -> str:
        """A new key: addresses with the old one are let in no more."""
        key = secrets.token_urlsafe(24)
        self._key.write(key)
        return key

    def live_types(self) -> list[str]:
        return sorted((kind for kind, count in self._open.items() if count > 0), key=str.casefold)

    def known_types(self) -> list[str]:
        return self._types.known(self._id)

    def add_type(self, kind: str) -> None:
        self._types.add(self._id, kind)

    def forget(self, kind: str) -> None:
        self._types.remove(self._id, kind)

    def refusal(self, key: str) -> str:
        if not self._enabled():
            return f"{self._title} is switched off under Connections → {self._title}"
        kept = self._key.read_or_empty()
        if not kept or not hmac.compare_digest(kept.encode(), str(key).encode()):
            return f"wrong key: copy the address again from Connections → {self._title}"
        return ""

    def opened(self, kind: str) -> None:
        self._open[kind] += 1
        self._types.add(self._id, kind)

    def received(self, kind: str, text: str) -> None:
        self._events.publish(self.event, {"type": kind, "text": text})

    def closed(self, kind: str) -> None:
        self._open[kind] -= 1
        if self._open[kind] <= 0:
            del self._open[kind]
