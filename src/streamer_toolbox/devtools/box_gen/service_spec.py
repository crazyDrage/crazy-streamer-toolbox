import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from streamer_toolbox.devtools.box_gen.box_spec import BoxSpec
from streamer_toolbox.devtools.box_gen.names import snake


@dataclass(frozen=True)
class ServiceSpec:
    """A spec file: the service (its action prefix, e.g. "mixitup"), the actions class to write, its default
    group and help, and the boxes. See docs/PLAN_box_maker.md for an example."""

    service: str
    class_name: str
    group: str
    description: str
    boxes: tuple[BoxSpec, ...]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ServiceSpec":
        for key in ("service", "class", "boxes"):
            if key not in data:
                raise ValueError(f"the spec needs {key!r}")
        boxes = tuple(BoxSpec.from_json(b) for b in data["boxes"])
        names = [b.name for b in boxes]
        doubles = sorted({n for n in names if names.count(n) > 1})
        if doubles:
            raise ValueError(f"two boxes with one name: {', '.join(doubles)}")
        return cls(snake(data["service"]), data["class"], data.get("group", ""), data.get("description", ""), boxes)

    @classmethod
    def read(cls, path: Path) -> "ServiceSpec":
        return cls.from_json(json.loads(path.read_text(encoding="utf-8")))
