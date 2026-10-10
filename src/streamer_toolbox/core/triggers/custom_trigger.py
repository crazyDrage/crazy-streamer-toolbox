from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.flows.flow_trigger import FlowTrigger

CUSTOM = "custom"  # the event a custom trigger sends; a flow listens with FlowTrigger("custom", {"trigger": name})


@dataclass(frozen=True)
class CustomTrigger:
    """A named trigger of his own (e.g. "lizard"): its sources are events that fire it (a Twitch redeem, a chat
    command, a VTS hotkey, a key; later YouTube ...), matched like a flow's triggers. Flows listen to the name,
    so one flow serves every platform. The Fire custom trigger action fires it too (SAMMI, Kit, a flow)."""

    name: str
    description: str = ""
    sources: tuple[FlowTrigger, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomTrigger":
        return cls(str(data["name"]), str(data.get("description", "")),
                   tuple(FlowTrigger(s["kind"], {k: v for k, v in s.items() if k != "kind"})
                         for s in data.get("sources", [])))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name}
        if self.description:
            data["description"] = self.description
        data["sources"] = [{"kind": s.kind, **s.match} for s in self.sources]
        return data

    def fired_by(self, kind: str, data: dict[str, Any]) -> bool:
        return kind != CUSTOM and any(s.matches(kind, data) for s in self.sources)
