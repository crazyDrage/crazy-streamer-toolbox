from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.widgets.boxes.widget_box import WidgetBox, LISTENERS
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore


class SendEventToWidgets(WidgetBox):
    name = "send_event"
    label = "Send event to widgets"
    help = "Sends your custom widgets an event as StreamElements would (listener + name, amount, message), e.g. " \
           "host-latest. A ...-latest one also counts in the widgets' session data. Gives how many widget pages " \
           "got it"
    group = "Widgets"
    hints = {"listener": "what the widget's code checks, e.g. tip-latest (any name works)",
             "widget": "empty = every widget",
             "extra": "more fields for the event, as an object like {\"tier\": \"1000\"}"}

    def __init__(self, hub: WidgetHub, store: WidgetStore) -> None:
        super().__init__(hub, store)
        self.options = {"listener": fixed_choices(list(LISTENERS)), "widget": self.widgets}

    async def run(self, listener: str, name: str = "", amount: float = 0, message: str = "",
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
