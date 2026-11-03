import re
from dataclasses import dataclass
from typing import Any

from streamer_toolbox.core.event_types.event_value import EventValue, names_in

NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


@dataclass(frozen=True)
class EventType:
    """Something that happens that widgets and alerts show (his round 78: Overlay → Events): a name (its box in
    flows will be "Send <name>"), its values, and the names other programs' code hears it as (StreamElements'
    follower-latest), so an imported widget is connected by itself. `default`: it came with the toolbox.
    `hidden`: left out of the list until "Show everything" (the defaults start hidden until something uses them)."""

    name: str
    values: tuple[EventValue, ...] = ()
    also_known_as: tuple[str, ...] = ()
    default: bool = False
    hidden: bool = False

    def value(self, name: str) -> EventValue | None:
        return next((v for v in self.values if v.name == name), None)

    @property
    def listener(self) -> str:
        """What a widget's code hears it as (onEventReceived's obj.detail.listener): its first other name, else
        its own."""
        return self.also_known_as[0] if self.also_known_as else self.name

    def filled(self, given: dict[str, Any]) -> dict[str, Any]:
        """Its values for one send: each from what the flow gave, else its default."""
        return {v.name: v.value(given.get(v.name)) for v in self.values}

    def known_as(self, name: str) -> bool:
        return name == self.name or name in self.also_known_as

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventType":
        return cls(str(data.get("name") or "event"),
                   tuple(EventValue.from_dict(v) for v in data.get("values", ()) if isinstance(v, dict)),
                   names_in(data.get("also_known_as", ())), bool(data.get("default", False)),
                   bool(data.get("hidden", False)))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name, "values": [v.to_dict() for v in self.values]}
        if self.also_known_as:
            data["also_known_as"] = list(self.also_known_as)
        if self.default:
            data["default"] = True
        if self.hidden:
            data["hidden"] = True
        return data


def check_event_name(name: str) -> str:
    name = str(name).strip()
    if not NAME.fullmatch(name):
        raise ValueError("an event's name is letters, digits, _ and - (no spaces), e.g. follow or lizard_redeem")
    return name
