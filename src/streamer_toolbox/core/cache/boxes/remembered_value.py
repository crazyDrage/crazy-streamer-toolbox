from collections.abc import AsyncIterator
from typing import Any

from streamer_toolbox.core.cache.remembered_values import RememberedValues, own_group
from streamer_toolbox.core.flows.current_box import current_box
from streamer_toolbox.core.interfaces.box import Box

FOUND, MISSING = "found", "no_value"
SET = "set"
MINUTE = 60


class RememberedValue(Box):
    """A value kept for a while, so a flow doesn't ask outside again (his round 90), e.g. Chat → this box (start):
    found → Send; no value → Twitch profile picture → Keep media locally → this box (set) → Send. Send reads this
    box's value on both ways. The values: RememberedValues (cache/remembered_values.json)."""

    name = "value"
    label = "Remembered value"
    help = ("'start': the value kept under Name, if it is younger than Max age (out 'found'), else out 'no value'. "
            "'set': keeps Value under Name, then out 'found'. Kept on this PC, also through a restart")
    group = "Remember"
    ports = (FOUND, MISSING)
    starts = {SET: ("value",)}
    flow_only = True
    typed = ("value",)
    outputs = {"value": "", "age": "number"}
    labels = {"key": "Name", "group": "Group", "max_age": "Max age (minutes)", "most": "Keep at most"}
    hints = {"key": "What it is kept under. Wire a value into it: the chat's user_id keeps one per chatter; "
                    "Build text joins several (platform and user_id)",
             "value": "Only read at 'set': what is kept",
             "group": "Empty = this box's own. Boxes with the same group share the values (a picture asked in one "
                      "flow is found in another)",
             "max_age": "Older, it counts as not there (out 'no value'), and it goes. Empty or 0 = a month",
             "most": "Values in the group; when it is fuller, the ones unused the longest go"}

    def __init__(self, values: RememberedValues) -> None:
        self._values = values

    async def run(self, key: Any, value: Any = "", group: str = "", max_age: float = 10,
                  most: int = 1000) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        key = str(key if key is not None else "").strip()
        if not key:
            raise ValueError("kept under which name? (Name is empty)")
        group = str(group or "").strip() or _own_group()
        seconds = float(max_age or 0) * MINUTE
        if self.started_at() == SET:
            self._values.set(group, key, value, seconds, int(most or 1000))
            port, given = FOUND, {"value": value, "age": 0}
        else:
            found, kept, age = self._values.get(group, key, seconds)
            port, given = (FOUND, {"value": kept, "age": round(age)}) if found else (MISSING, {"value": "", "age": 0})

        async def go() -> AsyncIterator[tuple[str, dict[str, Any]]]:
            yield port, given

        return go()


def _own_group() -> str:
    box = current_box.get()
    return own_group(*box) if box else "shared"
