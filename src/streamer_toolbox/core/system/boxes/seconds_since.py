from streamer_toolbox.core.system.boxes.time_box import TimeBox


class SecondsSince(TimeBox):
    name = "since"
    label = "Seconds since"
    help = "Seconds since a timestamp (from Date and time), e.g. to see how long ago the last raid was"
    group = "Time"
    flow_only = True

    async def run(self, timestamp: float) -> float:
        try:
            return round(self._clock() - float(timestamp), 3)
        except (TypeError, ValueError):
            raise ValueError(f"{timestamp!r} is not a timestamp (use Date and time's timestamp)") from None
