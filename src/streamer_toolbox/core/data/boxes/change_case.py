from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.data.boxes.text_shared import CASES
from streamer_toolbox.core.interfaces.box import Box


class ChangeCase(Box):
    name = "case"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "Change case"
    help = "UPPER, lower or Title Case"
    group = "Text"
    options = {"to": fixed_choices(CASES)}
    flow_only = True

    async def run(self, text: str, to: str = "lower") -> str:
        if to not in CASES:
            raise ValueError(f"to must be one of {', '.join(CASES)}, not {to!r}")
        return {"upper": str.upper, "lower": str.lower, "title": str.title}[to](str(text))
