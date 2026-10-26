from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_session import KINDS
from streamer_toolbox.core.widgets.widget_store import WidgetStore


LISTENERS = tuple(f"{kind}-latest" for kind in KINDS)


class WidgetBox(Box):
    """What the widget boxes share (not a box itself: it has no run).

    The Widgets box: send a widget an event from a flow, in StreamElements' words. For what a widget listens
    to but the toolbox has no event of its own for (a host, a merch sale, a custom name): a flow that knows about
    it tells the widgets."""

    def __init__(self, hub: WidgetHub, store: WidgetStore) -> None:
        self._hub = hub
        self._store = store

    async def widgets(self) -> list[str]:
        return self._store.names()
