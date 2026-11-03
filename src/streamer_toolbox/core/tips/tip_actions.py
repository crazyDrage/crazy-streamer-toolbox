from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.tips.boxes.tip_came_in import TipCameIn


class TipActions:
    """Tip came in: the way into the toolbox for tips / donations from any service (StreamElements, Streamlabs,
    Ko-fi, ...). The toolbox has no connection of its own to those yet, so whatever hears of the tip says so here:
    a flow (e.g. after a Web request), SAMMI, or another program over the API (POST /action/tip.fire). From then
    on a tip is an event like a follow or a cheer.

    One Box class per box, in boxes/."""

    def __init__(self, events: EventBus) -> None:
        self._events = events

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (TipCameIn(self._events),):
            actions.add_box(box, "tip")
