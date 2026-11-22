from pathlib import Path

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.testing.test_item import BOX, TRIGGER

ALL_CHECKS = ("works", "understandable", "usable")  # all three = "tested" in the record (his 11-21)


class FlowChecks:
    """His way through the test record (11-21): he builds flows and plays with them, then names them; every box
    and trigger in those flows gets his checks. Flows are found by file name or by their label, any case."""

    def __init__(self, folder: Path) -> None:
        self._store = FlowStore(folder)

    def find(self, names: list[str]) -> tuple[list[Flow], list[str]]:
        """The flows with these names, and the names nothing was found for."""
        flows = self._store.all()
        found, missing = [], []
        for name in names:
            wanted = name.strip().casefold()
            flow = next((f for f in flows if wanted in (f.name.casefold(), f.label.casefold())), None)
            if flow is None:
                missing.append(name)
            elif flow not in found:
                found.append(flow)
        return found, missing

    @staticmethod
    def keys(flows: list[Flow]) -> dict[str, list[str]]:
        """Each box and trigger in the flows (its row's key) → the labels of the flows it is in."""
        keys: dict[str, list[str]] = {}
        for flow in flows:
            for key in ([f"{TRIGGER}:{t.kind}" for t in flow.triggers]
                        + [f"{BOX}:{n.action}" for n in flow.nodes]):
                if flow.label not in keys.setdefault(key, []):
                    keys[key].append(flow.label)
        return keys
