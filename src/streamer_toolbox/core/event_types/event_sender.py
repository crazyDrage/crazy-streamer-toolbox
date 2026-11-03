from typing import Any

from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.event_types.event_type import EventType
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.widgets.widget_events import INPUT_EVENTS, input_event
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class EventSender:
    """Sends one event (his round 78: "one flow per event type, its box sends it to every widget and alert that
    uses it"): each widget that gets that event type gets it on its pages, in StreamElements' words; each alert
    of that type plays (when it is on and the amount is big enough). `only_to`: "widget <name>" or
    "alert <id>" sends it to that one only (a test, or a flow that was one widget's or alert's before)."""

    def __init__(self, events: EventTypeStore, widgets: WidgetStore, hub: WidgetHub, alerts: AlertStore,
                 queue: AlertQueue) -> None:
        self._events = events
        self._widgets = widgets
        self._hub = hub
        self._alerts = alerts
        self._queue = queue

    async def send(self, name: str, given: dict[str, Any], only_to: str = "") -> dict[str, Any]:
        """What reached whom: pages (widget pages that got it), alerts (alerts that play), in_front (alerts
        waiting before the first of them)."""
        kind = self._events.get(name)
        if kind is None:
            raise KeyError(f"there is no event {name!r} (any more): Overlay → Events")
        values = kind.filled(given)
        only_to = only_to.strip()
        pages = 0
        for widget_name in self._widgets.names():
            widget = self._widgets.get(widget_name)
            if widget and name in (widget.events or ()) and only_to in ("", f"widget {widget_name}"):
                pages += self._hub.send(kind.listener, widget_event(kind, values), widget_name)
        played, in_front = 0, None
        for rule in self._alerts.all():
            if rule.event == name and only_to in ("", f"alert {rule.id}") and rule.wants(values):
                waiting = await self._queue.show(rule.alert_for(values))
                in_front = waiting if in_front is None else in_front
                played += 1
        return {"pages": pages, "alerts": played, "in_front": in_front or 0}


def widget_event(kind: EventType, values: dict[str, Any]) -> dict[str, Any]:
    """What a widget's code gets as obj.detail.event: one that came with the toolbox in StreamElements' own
    shape (a chat message with its tags and emotes, a sub with "1000" as tier), then every value under its own
    name and its other names, where the shape has nothing of that name yet."""
    event = input_event(kind.name, values) if kind.default and kind.name in INPUT_EVENTS else {}
    for value in kind.values:
        for key in (value.name, *value.also_known_as):
            event.setdefault(key, values.get(value.name))
    return event
