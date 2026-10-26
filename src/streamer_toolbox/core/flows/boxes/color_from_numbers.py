from streamer_toolbox.core.data.box_value import to_number
from streamer_toolbox.core.interfaces.box import Box


class ColorFromNumbers(Box):
    name = "color"
    label = "Colour from numbers"
    help = "Makes a colour from three numbers 0-255 (red, green, blue), e.g. 255 128 0 = orange; gives it as hex " \
           "(#FF8000) for Tint model and other colour fields. Numbers outside 0-255 are kept inside"
    group = "Math"
    flow_only = True
    hints = {"red": "0-255", "green": "0-255", "blue": "0-255"}

    async def run(self, red: float = 0, green: float = 0, blue: float = 0) -> str:
        values = [to_number(v) for v in (red, green, blue)]
        if None in values:
            raise ValueError(f"Colour from numbers needs three numbers, got {red!r}, {green!r}, {blue!r}")
        return "#" + "".join(f"{min(max(round(v), 0), 255):02X}" for v in values)
