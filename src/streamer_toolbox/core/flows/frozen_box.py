import json
from dataclasses import dataclass
from typing import Any

from streamer_toolbox.core.flows.flow_wire import DONE, FlowWire


@dataclass(frozen=True)
class FrozenBox:
    """A box he froze (his idea of 2026-10-29): it ran once, and from then on gives what it gave then, `value`,
    without running in the flow; only "Run again" in the editor runs it (and keeps the new answer). Kept in the
    flow's file with the box, so a duplicated, exported or shared flow takes it along, and deleting the box
    deletes it.

    While frozen it has no run wire and no inputs: `wires` are the run wires it had (hidden, back with
    Unfreeze), `bridged` the ones that were added so the boxes before it lead to the ones after it (taken away
    again with Unfreeze). Its fields stay as they were: Run again uses them."""

    value: Any = None
    at: str = ""  # when it ran ("2026-10-29 21:14")
    wires: tuple[FlowWire, ...] = ()
    bridged: tuple[FlowWire, ...] = ()

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "FrozenBox":
        try:
            value = json.loads(data.get("value", "null"))
        except (TypeError, ValueError):
            value = data.get("value")
        return cls(value, str(data.get("at", "")), _wires(data.get("wires", [])), _wires(data.get("bridged", [])))

    def to_data(self) -> dict[str, Any]:
        """For the flow's file: the value as JSON text (a file can't hold "nothing", a result can)."""
        data: dict[str, Any] = {"at": self.at, "value": json.dumps(self.value, ensure_ascii=False, default=str)}
        if self.wires:
            data["wires"] = [_wire(w) for w in self.wires]
        if self.bridged:
            data["bridged"] = [_wire(w) for w in self.bridged]
        return data


def _wire(wire: FlowWire) -> dict[str, str]:
    return {"from": wire.source, "port": wire.port, "to": wire.target, **({"entry": wire.entry} if wire.entry else {})}


def _wires(data: Any) -> tuple[FlowWire, ...]:
    return tuple(FlowWire(str(w["from"]), str(w.get("port", DONE)), str(w["to"]), str(w.get("entry", "")))
                 for w in data or [] if isinstance(w, dict) and "from" in w and "to" in w)
