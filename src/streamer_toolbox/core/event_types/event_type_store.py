import json
from dataclasses import replace
from collections.abc import Callable
from pathlib import Path

from streamer_toolbox.core.event_types.default_event_types import DEFAULTS
from streamer_toolbox.core.event_types.event_type import EventType, check_event_name
from streamer_toolbox.core.event_types.event_value import EventValue


class EventTypeStore:
    """Overlay → Events' list in config/event_types.json, in his order (his round 78). The default types
    (default_event_types.DEFAULTS) are added once each, hidden: one he deleted stays gone, one a later version
    brings is added then (`defaults_added` remembers which came already). `flows_made`: the types whose own flow
    the toolbox made once (EventFlows): one he deleted isn't made again. on_change() after every change."""

    def __init__(self, path: Path) -> None:
        self._path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        self.on_change: Callable[[], None] | None = None
        self._types = {t.name: t for t in (EventType.from_dict(d) for d in data.get("types", ())
                                           if isinstance(d, dict) and d.get("name"))}
        self._defaults_added = [str(n) for n in data.get("defaults_added", ())]
        self._flows_made = [str(n) for n in data.get("flows_made", ())]
        new = [t for t in DEFAULTS if t.name not in self._defaults_added]
        for default in new:
            self._defaults_added.append(default.name)
            self._types.setdefault(default.name, default)
        if new:
            self._write()

    def all(self) -> list[EventType]:
        return list(self._types.values())

    def get(self, name: str) -> EventType | None:
        return self._types.get(name)

    def known_as(self, name: str) -> list[EventType]:
        """The types other programs' code hears as this name (subscriber-latest: sub, resub and gift)."""
        return [t for t in self._types.values() if t.known_as(name)]

    def show(self, name: str) -> None:
        """Something uses it now: out of hiding (his round 78: the defaults are hidden until used)."""
        found = self._types.get(name)
        if found is not None and found.hidden:
            self.save(name, replace(found, hidden=False))

    def flow_made(self, name: str) -> bool:
        return name in self._flows_made

    def mark_flow_made(self, name: str) -> None:
        if name not in self._flows_made:
            self._flows_made.append(name)
            self._write()

    def add(self, name: str = "event", values: tuple[EventValue, ...] = (),
            also_known_as: tuple[str, ...] = ()) -> EventType:
        """A new type, last in the list, shown, with a name no other type has."""
        base = check_event_name(name)
        name, number = base, 2
        while name in self._types:
            name, number = f"{base}_{number}", number + 1
        made = EventType(name, values, also_known_as)
        self._types[name] = made
        self._write()
        return made

    def save(self, old_name: str, changed: EventType) -> None:
        """Changes the type called old_name (a new name keeps its place), or adds it last."""
        new_name = check_event_name(changed.name)
        if new_name != old_name and new_name in self._types:
            raise ValueError(f"there is an event {new_name!r} already")
        self._types = {(new_name if n == old_name else n): (changed if n == old_name else t)
                       for n, t in self._types.items()}
        self._types.setdefault(new_name, changed)
        self._flows_made = [new_name if n == old_name else n for n in self._flows_made]
        self._write()

    def delete(self, name: str) -> None:
        if self._types.pop(name, None) is not None:
            self._write()

    def _write(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"types": [t.to_dict() for t in self._types.values()],
                                          "defaults_added": self._defaults_added, "flows_made": self._flows_made},
                                         indent=2, ensure_ascii=False),
                              encoding="utf-8")
        if self.on_change:
            self.on_change()
