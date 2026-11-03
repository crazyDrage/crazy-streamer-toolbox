from streamer_toolbox.core.data.box_value import to_number
from streamer_toolbox.core.interfaces.box import Box

UNITS = (("d", 86400), ("h", 3600), ("min", 60), ("s", 1))


class DurationText(Box):
    """Seconds as words people read: 4980 → "1 h 23 min". The biggest unit and the one below it (left out when
    0), rounded down: 1 h 23 min 40 s says 1 h 23 min, 1 d 0 h 5 min says 1 d. Round 68: what !uptime was
    waiting for."""

    name = "duration"
    label = "Seconds as text"
    help = "A number of seconds as text, e.g. 4980 → 1 h 23 min (for !uptime, with Channel info's uptime_seconds)"
    group = "Time"
    data_only = True  # no run wire: only works out a value from its input (his rule, round 62 A)
    hints = {"seconds": "e.g. 4980, or wire Channel info's uptime_seconds in"}

    async def run(self, seconds: float) -> str:
        number = to_number(seconds)
        if number is None:
            raise ValueError(f"{seconds!r} is not a number of seconds")
        left = max(0, int(number))
        first = next(i for i, (_, size) in enumerate(UNITS) if left >= size or size == 1)
        unit, size = UNITS[first]
        text = f"{left // size} {unit}"
        if first + 1 < len(UNITS):
            next_unit, next_size = UNITS[first + 1]
            if (left % size) // next_size:
                text += f" {(left % size) // next_size} {next_unit}"
        return text
