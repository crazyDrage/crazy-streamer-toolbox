from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus

EVENT = "heartrate"


class HeartRate:
    """The streamer's heart rate, whichever service tells it (Pulsoid, HypeRate): the last value, a
    `heartrate` event each time it changes (trigger "Heart rate changed") and a box that reads it, also
    usable as a Live value in any field."""

    def __init__(self, events: EventBus) -> None:
        self._events = events
        self._bpm = 0
        self._source = ""

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("heartrate.get", self.get, "The heart rate now, in beats per minute (0 before a service "
                    "told one)", "Get heart rate", live=True, outputs={"bpm": "number", "source": "text"})

    def beat(self, bpm: Any, source: str) -> None:
        """A service told a heart rate. Anything that isn't a number above 0 is ignored."""
        try:
            bpm = int(bpm)
        except (TypeError, ValueError):
            return
        if bpm <= 0 or (bpm, source) == (self._bpm, self._source):
            return
        self._bpm, self._source = bpm, source
        self._events.publish(EVENT, {"bpm": bpm, "source": source})

    async def get(self) -> dict[str, Any]:
        return {"bpm": self._bpm, "source": self._source}
