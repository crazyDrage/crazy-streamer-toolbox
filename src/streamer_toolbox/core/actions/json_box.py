from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.actions.json_box_field import JsonBoxField


@dataclass(frozen=True)
class JsonBox:
    """One box that is written in a JSON file (see JsonBoxes for the file): `name` is the box's name after its
    category ("open_source_projector" → obs.open_source_projector), `request` what is sent to the program,
    `fixed` the data every such request carries besides the fields, `group` the box's sub group in the Add box
    window (else the file's), `outputs` the keys the program's answer always has (each a data dot)."""

    name: str
    request: str
    label: str = ""
    help: str = ""
    fields: tuple[JsonBoxField, ...] = ()
    fixed: dict[str, Any] = field(default_factory=dict)
    group: str = ""
    flow_only: bool = False
    outputs: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any], group: str = "") -> "JsonBox":
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown or not data.get("name") or not data.get("request"):
            raise ValueError(f"a box needs \"name\" and \"request\" and may have label, help, fields, fixed, group, "
                             f"flow_only, outputs (got {', '.join(sorted(data))})")
        fields = tuple(JsonBoxField.from_dict(f) for f in data.get("fields", ()))
        names = [f.name for f in fields]
        if len(set(names)) != len(names):
            raise ValueError(f"box {data['name']!r} has a field name twice")
        return cls(**{**data, "fields": fields, "fixed": dict(data.get("fixed", {})),
                      "group": data.get("group", group), "outputs": tuple(data.get("outputs", ()))})
