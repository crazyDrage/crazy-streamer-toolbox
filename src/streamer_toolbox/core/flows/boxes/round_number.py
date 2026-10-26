from streamer_toolbox.core.data.box_value import to_number
from streamer_toolbox.core.interfaces.box import Box


class RoundNumber(Box):
    name = "round"
    label = "Round"
    help = "Rounds a number to that many decimals (0 = a whole number)"
    group = "Math"
    flow_only = True
    data_only = True  # no run wire: it runs whenever a box needs its value (his OPEN 92)
    hints = {"decimals": "0 = a whole number, 2 = like 1.25"}

    async def run(self, number: float, decimals: int = 0) -> float:
        value = to_number(number)
        if value is None:
            raise ValueError(f"{number!r} is not a number")
        rounded = round(value, int(decimals))
        return int(rounded) if int(decimals) <= 0 else rounded
