from typing import Any

from streamer_toolbox.connections.heartrate.boxes.get_heart_rate import GetHeartRate
from streamer_toolbox.connections.heartrate.boxes.heart_rate_shared import EVENT
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.events.event_bus import EventBus


class HeartRate:
    """The streamer's heart rate, whichever service tells it (Pulsoid, HypeRate): the last value, a
    `heartrate` event each time it changes (trigger "Heart rate changed"; with the one before as previous_bpm,
    0 for the first, so "rises above" / "falls below" can tell a crossing) and a box that reads it, also usable
    as a Live value in any field."""

    def __init__(self, events: EventBus) -> None:
        self._events = events
        self._bpm = 0
        self._source = ""

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (GetHeartRate(self),):
            actions.add_box(box, "heartrate")

    def beat(self, bpm: Any, source: str) -> None:
        """A service told a heart rate. Anything that isn't a number above 0 is ignored."""
        try:
            bpm = int(bpm)
        except (TypeError, ValueError):
            return
        if bpm <= 0 or (bpm, source) == (self._bpm, self._source):
            return
        previous, self._bpm, self._source = self._bpm, bpm, source
        self._events.publish(EVENT, {"bpm": bpm, "previous_bpm": previous, "source": source})

    async def get(self) -> dict[str, Any]:
        return {"bpm": self._bpm, "source": self._source}
