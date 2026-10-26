from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.widgets.boxes.send_event_to_widgets import SendEventToWidgets
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class WidgetActions:
    """The Widgets box: send a widget an event from a flow, in StreamElements' words. For what a widget listens
    to but the toolbox has no event of its own for (a host, a merch sale, a custom name): a flow that knows about
    it tells the widgets.

    One Box class per box, in boxes/."""

    def __init__(self, hub: WidgetHub, store: WidgetStore) -> None:
        self._hub = hub
        self._store = store

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (SendEventToWidgets(self._hub, self._store),):
            actions.add_box(box, "widget")
