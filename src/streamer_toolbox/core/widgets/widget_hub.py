import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from streamer_toolbox.core.overlay.sent_messages import SentMessages
from streamer_toolbox.core.widgets.widget_events import se_event, test_event
from streamer_toolbox.core.widgets.widget_session import WidgetSession

log = logging.getLogger(__name__)
RESEND_SECONDS = 600  # a widget page that comes back gets the events of the last 10 minutes it missed
LOADED = "widget.loaded"  # a widget's page was opened (not one that only came back): his round 74's start trigger


class WidgetHub:
    """Events for the widget pages. Each open widget page (a Browser source in OBS, or the toolbox's preview)
    listens with an inbox. A flow sends one widget an event (EventSender, his round 78; round 74: nothing reaches a
    widget by itself any more) as {"type": "event", listener, event}, a ...-latest one followed by the session
    data. The session data (latest names, counts: what a widget reads when it loads) still follows every toolbox
    event by itself (handle). Unlike alerts there is no line: widgets decide themselves what to do with an
    event."""

    def __init__(self, session: WidgetSession | None = None,
                 channel: Callable[[], dict[str, str]] | None = None) -> None:
        self.session = session or WidgetSession()
        self._channel = channel or (lambda: {})  # the streamer's name and Twitch id, for a test chat command
        self._inboxes: dict[asyncio.Queue, tuple[str, bool]] = {}  # inbox → (widget, is a preview)
        # events a widget page in OBS didn't confirm (api/overlay_line.py): ("21:14:05", widget, listener, id).
        # A page that comes back gets them again (self.sent).
        self.missed: deque[tuple[str, str, str, int]] = deque(maxlen=20)
        self.sent = SentMessages(RESEND_SECONDS)
        # a page was opened: (widget, is a preview); the toolbox makes it the event LOADED, so a flow can send
        # what the widget shows at once (the last follower, ...)
        self.on_loaded: Callable[[str, bool], None] = lambda widget, preview: None

    def listen(self, widget: str, preview: bool = False) -> asyncio.Queue:
        inbox: asyncio.Queue = asyncio.Queue()
        self._inboxes[inbox] = (widget, preview)
        return inbox

    def greeting(self, widget: str, run: str | None = None, after: int | None = None) -> list[dict[str, Any]]:
        """What a widget page gets first on its line: {"type": "hello"} (the run, the newest id), and for a page
        that comes back (after: the last id it got) what it missed."""
        return [self.sent.hello()] + (self.sent.since(run, after, widget) if after is not None else [])

    def loaded(self, widget: str, preview: bool = False) -> None:
        """A page of the widget was opened (OBS loaded the Browser source, or the toolbox's preview)."""
        self.on_loaded(widget, preview)

    def stop_listening(self, inbox: asyncio.Queue) -> None:
        self._inboxes.pop(inbox, None)

    def not_arrived(self, widget: str, message: dict[str, Any]) -> None:
        """A widget page in OBS didn't confirm this event (its line broke): kept and logged."""
        if message.get("type") != "event":
            return
        if any(entry[3] == message.get("id") for entry in self.missed):  # two pages missed it: once is enough
            return
        self.missed.append((time.strftime("%H:%M:%S"), widget, message.get("listener", ""), message.get("id", 0)))
        log.warning("event %r didn't reach widget %r in OBS (its line broke)", message.get("listener"), widget)

    def arrived(self, message: dict[str, Any]) -> None:
        """A page confirmed this message: an event that was missed came through after all (sent again)."""
        for entry in [entry for entry in self.missed if entry[3] == message.get("id")]:
            self.missed.remove(entry)
            log.info("event %r reached widget %r in OBS late (sent again)", entry[2], entry[1])

    def pages(self, widget: str) -> int:
        """How many Browser sources show that widget right now (the toolbox's preview isn't one)."""
        return sum(1 for name, preview in self._inboxes.values() if name == widget and not preview)

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        """EventBus → the session data (latest names, counts), in StreamElements' words. No page is told: what a
        widget shows comes from flows (send)."""
        mapped = se_event(kind, data)
        if mapped is not None:
            self.session.add(*mapped)

    def send(self, listener: str, event: dict[str, Any], widget: str) -> int:
        """An event from a flow (its Send box, EventSender) to that widget's pages; a ...-latest one is
        followed by the session data (the real event already counted in it, handle). How many pages got it."""
        told = self._tell({"type": "event", "listener": listener, "event": self._in_channel(listener, event)},
                          widget)
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
        stamped = self.sent.stamp(message, widget)
        for inbox in told:
            inbox.put_nowait(stamped)
        return len(told)
