import json
from dataclasses import replace
from pathlib import Path

from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.triggers.custom_trigger import CustomTrigger


class CustomTriggerStore:
    """The custom triggers in config/custom_triggers.json, in the order he made them. Names are unique (ignoring
    upper/lower case); renaming a trigger is the library's job for the flows that listen to it."""

    def __init__(self, path: Path) -> None:
        self._path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        self._triggers = [CustomTrigger.from_dict(t) for t in data.get("triggers", [])]

    def all(self) -> list[CustomTrigger]:
        return list(self._triggers)

    def names(self) -> list[str]:
        return [t.name for t in self._triggers]

    def get(self, name: str) -> CustomTrigger | None:
        return next((t for t in self._triggers if t.name.casefold() == name.casefold()), None)

    def add(self, name: str, description: str = "") -> CustomTrigger:
        name = name.strip()
        if not name:
            raise ValueError("a custom trigger needs a name")
        if self.get(name):
            raise ValueError(f"there's a custom trigger {name!r} already")
        trigger = CustomTrigger(name, description.strip())
        self._triggers.append(trigger)
        self._save()
        return trigger

    def update(self, old_name: str, trigger: CustomTrigger) -> None:
        """Replaces it (a new name, description or sources)."""
        other = self.get(trigger.name)
        if other and other.name.casefold() != old_name.casefold():
            raise ValueError(f"there's a custom trigger {trigger.name!r} already")
        self._triggers = [trigger if t.name.casefold() == old_name.casefold() else t for t in self._triggers]
        self._save()

    def delete(self, name: str) -> None:
        self._triggers = [t for t in self._triggers if t.name.casefold() != name.casefold()]
        self._save()

    def add_source(self, name: str, source: FlowTrigger) -> None:
        trigger = self.get(name) or self.add(name)
        if source not in trigger.sources:
            self.update(trigger.name, replace(trigger, sources=(*trigger.sources, source)))

    def remove_source(self, name: str, source: FlowTrigger) -> None:
        trigger = self.get(name)
        if trigger:
            self.update(trigger.name, replace(trigger, sources=tuple(s for s in trigger.sources if s != source)))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"triggers": [t.to_dict() for t in self._triggers]}, indent=2,
                                         ensure_ascii=False), encoding="utf-8")
