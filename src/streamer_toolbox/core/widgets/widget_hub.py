import asyncio
from collections.abc import Callable
from typing import Any

from streamer_toolbox.core.widgets.widget_events import se_event, test_event
from streamer_toolbox.core.widgets.widget_session import WidgetSession


class WidgetHub:
    """Events for the widget pages. Each open widget page (a Browser source in OBS, or the toolbox's preview)
    listens with an inbox; a toolbox event that StreamElements has a word for goes to every one of them as
    {"type": "event", listener, event}, followed by the session data. Unlike alerts there is no line: widgets
    decide themselves what to do with an event."""

    def __init__(self, session: WidgetSession | None = None,
                 channel: Callable[[], dict[str, str]] | None = None) -> None:
        self.session = session or WidgetSession()
        self._channel = channel or (lambda: {})  # the streamer's name and Twitch id, for a test chat command
        self._inboxes: dict[asyncio.Queue, tuple[str, bool]] = {}  # inbox → (widget, is a preview)

    def listen(self, widget: str, preview: bool = False) -> asyncio.Queue:
        inbox: asyncio.Queue = asyncio.Queue()
        self._inboxes[inbox] = (widget, preview)
        return inbox

    def stop_listening(self, inbox: asyncio.Queue) -> None:
        self._inboxes.pop(inbox, None)

    def pages(self, widget: str) -> int:
        """How many Browser sources show that widget right now (the toolbox's preview isn't one)."""
        return sum(1 for name, preview in self._inboxes.values() if name == widget and not preview)

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        """EventBus → every widget page, in StreamElements' words."""
        mapped = se_event(kind, data)
        if mapped is None:
            return
        self.session.add(*mapped)
        self._tell({"type": "event", "listener": mapped[0], "event": self._in_channel(*mapped)})
        if mapped[0].endswith("-latest"):  # chat messages and deletions change no session data
            self._tell({"type": "session", "session": self.session.data})

    def send(self, listener: str, event: dict[str, Any], widget: str | None = None) -> int:
        """An event from a flow (the Send event to widgets box): to one widget's pages or to all; a ...-latest
        one counts in the session data like a real one. How many pages got it."""
        self.session.add(listener, event)
        told = self._tell({"type": "event", "listener": listener, "event": event}, widget)
        if listener.endswith("-latest"):
            self._tell({"type": "session", "session": self.session.data}, widget)
        return told

    def test(self, widget: str, listener: str, text: str = "") -> int:
        """A test event for one widget's pages only (the session data stays as it is); how many got it. text: a
        chat message's text, sent as the streamer (to try a widget's chat commands)."""
        event = self._in_channel(listener, test_event(listener, text, self._channel()))
        return self._tell({"type": "event", "listener": listener, "event": event}, widget)

    def button(self, widget: str, field: str, value: Any = "") -> int:
        """A button field was pressed in the widget's settings. StreamElements sends that as listener
        "event:test" with the event saying listener "widget-button" (helper libraries like se-tools check both)."""
        return self._tell({"type": "event", "listener": "event:test",
                           "event": {"listener": "widget-button", "field": field, "value": value}}, widget)

    def reload(self, widget: str) -> int:
        """The widget's code or settings changed: its pages load again."""
        return self._tell({"type": "reload"}, widget)

    def _in_channel(self, listener: str, event: dict[str, Any]) -> dict[str, Any]:
        """A chat message says which channel it was written in: the streamer's (multi channel chat widgets tell
        his chat from the others by it)."""
        if listener == "message" and "data" in event:
            event["data"]["channel"] = self._channel().get("username", "")
        return event

    def _tell(self, message: dict[str, Any], widget: str | None = None) -> int:
        told = [inbox for inbox, (name, _) in self._inboxes.items() if widget is None or name == widget]
        for inbox in told:
            inbox.put_nowait(message)
        return len(told)
