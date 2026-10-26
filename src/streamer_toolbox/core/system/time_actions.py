import time
from collections.abc import Callable

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.system.boxes.date_and_time import DateAndTime
from streamer_toolbox.core.system.boxes.seconds_since import SecondsSince


class TimeActions:
    """Date and time boxes (SAMMI's date/time variables like {HH}), e.g. the hour the stream started, or how long
    ago something was (keep a timestamp in a variable).

    One Box class per box, in boxes/."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock  # tests set the time

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (DateAndTime(self._clock), SecondsSince(self._clock)):
            actions.add_box(box, "time")
