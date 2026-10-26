from typing import Any

from streamer_toolbox.core.actions.fixed_choices import fixed_choices
from streamer_toolbox.core.data.boxes.object_shared import _object
from streamer_toolbox.core.interfaces.box import Box

SHOW = ("changed", "same", "all")
MISSING = None  # what a key has on the side it isn't on


class CompareObjects(Box):
    name = "compare"
    label = "Compare objects"
    help = "What changed between two objects (e.g. the last saved one and a new one), what stayed the same, or " \
           "all of it. Keys inside keys are compared one by one, as paths (physics.wind)"
    group = "Read"
    flow_only = True
    options = {"show": fixed_choices(SHOW)}
    hints = {"show": "changed: each key with before and after (one that is new or gone has empty there) · same: "
                     "the keys that stayed, with their value · all: every key with before, after and changed"}
    outputs = {"values": "object", "keys": "list", "changed": "yes/no"}

    async def run(self, before: Any, after: Any, show: str = "changed") -> dict[str, Any]:
        if show not in SHOW:
            raise ValueError(f"show must be one of {', '.join(SHOW)}, not {show!r}")
        old, new = _flat(_object(before)), _flat(_object(after))
        keys = list(old) + [key for key in new if key not in old]
        differs = {key for key in keys
                   if old.get(key, MISSING) != new.get(key, MISSING) or (key in old) != (key in new)}
        if show == "changed":
            values = {key: {"before": old.get(key, MISSING), "after": new.get(key, MISSING)}
                      for key in keys if key in differs}
        elif show == "same":
            values = {key: new[key] for key in keys if key not in differs}
        else:
            values = {key: {"before": old.get(key, MISSING), "after": new.get(key, MISSING),
                            "changed": key in differs} for key in keys}
        return {"values": values, "keys": list(values), "changed": bool(differs)}


def _flat(value: dict[str, Any], path: str = "") -> dict[str, Any]:
    """{"physics": {"wind": 0}} → {"physics.wind": 0}; an empty object and a list stay one value."""
    flat: dict[str, Any] = {}
    for key, inner in value.items():
        name = f"{path}{key}"
        if isinstance(inner, dict) and inner:
            flat.update(_flat(inner, name + "."))
        else:
            flat[name] = inner
    return flat
