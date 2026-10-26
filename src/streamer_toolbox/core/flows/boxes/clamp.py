from streamer_toolbox.core.data.box_value import to_number
from streamer_toolbox.core.interfaces.box import Box


class Clamp(Box):
    name = "clamp"
    label = "Clamp"
    help = "Keeps a number between lowest and highest, e.g. a power a viewer typed into 1 to 10"
    group = "Math"
    flow_only = True
    data_only = True  # no run wire: it runs whenever a box needs its value (his OPEN 92)
    labels = {"lowest": "At least", "highest": "At most"}

    async def run(self, number: float, lowest: float = 0, highest: float = 100) -> float:
        value, low, high = to_number(number), to_number(lowest), to_number(highest)
        if value is None or low is None or high is None:
            raise ValueError(f"Clamp needs numbers, got {number!r}, {lowest!r}, {highest!r}")
        result = min(max(value, low), high)
        return int(result) if result == int(result) else result
