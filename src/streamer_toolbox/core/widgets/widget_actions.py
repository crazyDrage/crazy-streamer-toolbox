from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_session import KINDS
from streamer_toolbox.core.widgets.widget_store import WidgetStore

LISTENERS = tuple(f"{kind}-latest" for kind in KINDS)


class WidgetActions:
    """The Widgets box: send a widget an event from a flow, in StreamElements' words. For what a widget listens
    to but the toolbox has no event of its own for (a host, a merch sale, a custom name): a flow that knows about
    it tells the widgets."""

    def __init__(self, hub: WidgetHub, store: WidgetStore) -> None:
        self._hub = hub
        self._store = store

    def add_to(self, actions: ActionRegistry) -> None:
        async def listeners() -> list[str]:
            return list(LISTENERS)

        async def widgets() -> list[str]:
            return self._store.names()

        actions.add("widget.send_event", self.send_event, "Sends your custom widgets an event as StreamElements "
                    "would (listener + name, amount, message), e.g. host-latest. A ...-latest one also counts "
                    "in the widgets' session data. Gives how many widget pages got it", "Send event to widgets",
                    group="Widgets", options={"listener": listeners, "widget": widgets},
                    hints={"listener": "what the widget's code checks, e.g. tip-latest (any name works)",
                           "widget": "empty = every widget",
                           "extra": "more fields for the event, as an object like {\"tier\": \"1000\"}"})

    async def send_event(self, listener: str, name: str = "", amount: float = 0, message: str = "",
                         widget: str = "", extra: Any = "") -> int:
        if not str(listener).strip():
            raise ValueError("which event? (listener is empty, e.g. tip-latest)")
        if extra not in (None, "") and not isinstance(extra, dict):
            raise ValueError(f"extra must be an object like {{\"tier\": \"1000\"}}, not {extra!r}")
        listener = str(listener).strip()
        number = float(amount) if amount not in (None, "") else 0
        event = {"type": listener.removesuffix("-latest"), "name": str(name),
                 "amount": int(number) if number == int(number) else number, "message": str(message),
                 **(extra or {})}
        return self._hub.send(listener, event, str(widget).strip() or None)
