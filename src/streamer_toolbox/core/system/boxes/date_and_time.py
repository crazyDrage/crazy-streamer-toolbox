from datetime import datetime
from typing import Any

from streamer_toolbox.core.system.boxes.time_box import TimeBox, WEEKDAYS


class DateAndTime(TimeBox):
    name = "now"
    label = "Date and time"
    help = "The date and time now: hour, minute, weekday, date, time, timestamp (seconds, for Seconds since) and " \
           "text in your format (e.g. %H:%M = 21:05, %d.%m.%Y = 01.10.2026; empty = 2026-10-01 21:05)"
    group = "Time"
    live = True
    outputs = {"hour": "number", "minute": "number", "second": "number", "weekday": "text",
               "date": "text", "time": "text", "timestamp": "number", "text": "text"}

    async def run(self, format: str = "") -> dict[str, Any]:
        stamp = self._clock()
        moment = datetime.fromtimestamp(stamp)
        return {"hour": moment.hour, "minute": moment.minute, "second": moment.second,
                "weekday": WEEKDAYS[moment.weekday()], "date": moment.strftime("%Y-%m-%d"),
                "time": moment.strftime("%H:%M:%S"), "timestamp": round(stamp, 3),
                "text": moment.strftime(format or "%Y-%m-%d %H:%M")}
