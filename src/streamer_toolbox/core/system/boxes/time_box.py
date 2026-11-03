import time
from collections.abc import Callable

from streamer_toolbox.core.interfaces.box import Box


WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class TimeBox(Box):
    """What the time boxes share (not a box itself: it has no run).

    Date and time boxes (SAMMI's date/time variables like {HH}), e.g. the hour the stream started, or how long
    ago something was (keep a timestamp in a variable)."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock  # tests set the time
