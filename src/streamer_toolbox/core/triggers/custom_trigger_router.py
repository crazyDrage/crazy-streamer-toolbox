from typing import Any

from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.triggers.custom_trigger import CUSTOM
from streamer_toolbox.core.triggers.custom_trigger_store import CustomTriggerStore


class CustomTriggerRouter:
    """Listens on the EventBus: an event that is a source of a custom trigger fires it, i.e. publishes a "custom"
    event with the source event's data plus trigger (its name), platform (twitch, ...; "" if the event has none) and
    source (the event kind, e.g. twitch.redeem). Flows with a Custom trigger start from that. A custom event never
    fires another custom trigger (no loops)."""

    def __init__(self, store: CustomTriggerStore, events: EventBus) -> None:
        self._store = store
        self._events = events

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        if kind == CUSTOM:
            return
        for trigger in self._store.all():
            if trigger.fired_by(kind, data):
                self._events.publish(CUSTOM, {**data, "trigger": trigger.name,
                                              "platform": data.get("platform", ""), "source": kind})
