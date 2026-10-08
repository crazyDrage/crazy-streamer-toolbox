from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus

TIP = "tip"  # the event a tip sends: flows with a Tip trigger start, the Tip alert shows, widgets get tip-latest


class TipActions:
    """Tip came in: the way into the toolbox for tips / donations from any service (StreamElements, Streamlabs,
    Ko-fi, ...). The toolbox has no connection of its own to those yet, so whatever hears of the tip says so here:
    a flow (e.g. after a Web request), SAMMI, or another program over the API (POST /action/tip.fire). From then
    on a tip is an event like a follow or a cheer."""

    def __init__(self, events: EventBus) -> None:
        self._events = events

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("tip.fire", self.fire, "Tells the toolbox a tip / donation came in: flows with a Tip trigger "
                    "start, the Tip alert shows, widgets get it as tip-latest. For services the toolbox has no "
                    "connection to: call it from a flow or over the API", "Tip came in", group="Tips",
                    hints={"amount": "e.g. 5 or 4.99", "currency": "e.g. EUR, USD (shown in alerts)",
                           "source": "where it came from, e.g. streamelements, kofi (any word; flows can check it "
                                     "as platform)"})

    async def fire(self, user: str, amount: float, currency: str = "", message: str = "",
                   source: str = "") -> dict[str, Any]:
        try:
            value = round(float(amount), 2)
        except (TypeError, ValueError):
            raise ValueError(f"amount must be a number like 5 or 4.99, not {amount!r}") from None
        if value <= 0:
            raise ValueError(f"a tip's amount must be above 0, got {value:g}")
        tip = {"user": str(user).strip(), "amount": int(value) if value == int(value) else value,
               "currency": str(currency).strip().upper(), "message": str(message), "platform": str(source).strip()}
        self._events.publish(TIP, tip)
        return tip
