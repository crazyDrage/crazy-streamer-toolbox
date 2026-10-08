from typing import Any


class EventCounter:
    """LISTENS to what happens in the toolbox: `ctx.on_event(counter.heard)` makes the toolbox call `heard`
    for every event: a follow, a redeem, a chat message, a key, another plugin's event.

    `kind` is the event's name ("twitch.follow", "follow", "example.blinked"); `data` is a dict with its
    fields (which ones: `src/streamer_toolbox/core/events/event_fields.py`). This one only counts. A real
    plugin would look for the kinds it cares about: `if kind == "follow": ...`.

    Be careful with what events carry (chat text, names): don't write it into a log or a file."""

    def __init__(self) -> None:
        self.count = 0
        self.last = ""

    async def heard(self, kind: str, data: dict[str, Any]) -> None:
        if kind == "timer":  # timers tick every second for flows that use them; not worth counting
            return
        self.count += 1
        self.last = kind
