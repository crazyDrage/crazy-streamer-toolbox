from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.interfaces.box import Box


TIP = "tip"


class TipBox(Box):
    """What the tip boxes share (not a box itself: it has no run).

    Tip came in: the way into the toolbox for tips / donations from any service (StreamElements, Streamlabs,
    Ko-fi, ...). The toolbox has no connection of its own to those yet, so whatever hears of the tip says so here:
    a flow (e.g. after a Web request), SAMMI, or another program over the API (POST /action/tip.fire). From then
    on a tip is an event like a follow or a cheer."""

    def __init__(self, events: EventBus) -> None:
        self._events = events
