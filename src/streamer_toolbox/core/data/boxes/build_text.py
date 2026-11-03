from typing import Any

from streamer_toolbox.core.interfaces.box import Box


class BuildText(Box):
    """His notes of 10-29: "a box to build text: {name} just gave {amount} Bits. The input can add values (like
    the output box)". Its values are lines he names (+ Add value, like End's), each with a dot to wire into."""

    name = "build"
    label = "Build text"
    help = "Puts values into a text: {name} in the text is the value of that name. + Add value for each one; wire " \
           "into its dot or type it. E.g. {name} just gave {amount} bits!"
    group = "Text"
    flow_only = True
    named_lines = True
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A)
    hints = {"text": "e.g. {name} just gave {amount} bits!"}

    async def run(self, text: str = "", **values: Any) -> str:
        for name, value in values.items():
            text = text.replace("{" + name + "}", "" if value is None else str(value))
        return text
