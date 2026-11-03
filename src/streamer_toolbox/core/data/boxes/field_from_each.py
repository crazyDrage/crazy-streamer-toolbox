from typing import Any

from streamer_toolbox.core.data.box_value import to_list
from streamer_toolbox.core.interfaces.box import Box


class FieldFromEach(Box):
    """His round 81: Scene sources gives objects ({"source": "so-event", "visible": false, ...}); he needed just
    the names, ["so-event"]."""

    name = "field_from_each"
    data_only = True  # no run wire: only works out a value from its inputs (his rule, round 62 A / notes 10-29)
    label = "Field from each"
    help = "A list of objects → a list of one field of each, e.g. field source: [{\"source\": \"so-event\", ...}] → " \
           "[\"so-event\"]. Objects without that field are left out"
    group = "New list"
    flow_only = True
    hints = {"field": "the name of the field, e.g. source"}

    async def run(self, items: Any, field: str) -> list[Any]:
        field = str(field).strip()
        if not field:
            raise ValueError("Which field? e.g. source")
        return [item[field] for item in to_list(items) if isinstance(item, dict) and field in item]
