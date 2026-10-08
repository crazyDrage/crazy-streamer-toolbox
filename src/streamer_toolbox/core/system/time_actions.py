import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class TimeActions:
    """Date and time boxes (SAMMI's date/time variables like {HH}), e.g. the hour the stream started, or how long
    ago something was (keep a timestamp in a variable)."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock  # tests set the time

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("time.now", self.now, "The date and time now: hour, minute, weekday, date, time, timestamp "
                    "(seconds, for Seconds since) and text in your format (e.g. %H:%M = 21:05, %d.%m.%Y = "
                    "01.10.2026; empty = 2026-10-01 21:05)", "Date and time", group="Time", live=True,
                    outputs={"hour": "number", "minute": "number", "second": "number", "weekday": "text",
                             "date": "text", "time": "text", "timestamp": "number", "text": "text"})
        actions.add("time.since", self.since, "Seconds since a timestamp (from Date and time), e.g. to see how long "
                    "ago the last raid was", "Seconds since", group="Time", flow_only=True)

    async def now(self, format: str = "") -> dict[str, Any]:
        stamp = self._clock()
        moment = datetime.fromtimestamp(stamp)
        return {"hour": moment.hour, "minute": moment.minute, "second": moment.second,
                "weekday": WEEKDAYS[moment.weekday()], "date": moment.strftime("%Y-%m-%d"),
                "time": moment.strftime("%H:%M:%S"), "timestamp": round(stamp, 3),
                "text": moment.strftime(format or "%Y-%m-%d %H:%M")}

    async def since(self, timestamp: float) -> float:
        try:
            return round(self._clock() - float(timestamp), 3)
        except (TypeError, ValueError):
            raise ValueError(f"{timestamp!r} is not a timestamp (use Date and time's timestamp)") from None
