import tomllib
from dataclasses import replace
from typing import Any

import tomlkit

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_store import FlowStore

PACK_KEY = "toolbox_flows"  # in a file: this is a folder of flows, and the format's number
FORMAT = 1
PREFIX = "flow."


class FlowPack:
    """A folder of flows as one file, to give to someone else: `toolbox_flows = 1`, `folder`, and one [[flows]]
    table per flow (its file name as `name`, then what its own .toml holds). The names are in it because flows
    use each other as boxes (flow.<name>); renamed() keeps those boxes right when a name is taken on import."""

    def __init__(self, folder: str, flows: tuple[Flow, ...]) -> None:
        self.folder = folder
        self.flows = flows

    def to_text(self) -> str:
        return tomlkit.dumps({PACK_KEY: FORMAT, "folder": self.folder,
                              "flows": [{"name": f.name, **FlowStore.to_data(f)} for f in self.flows]})

    @staticmethod
    def is_pack(data: dict[str, Any]) -> bool:
        return PACK_KEY in data

    @classmethod
    def from_text(cls, text: str) -> "FlowPack":
        return cls.from_data(tomllib.loads(text))

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "FlowPack":
        if data.get(PACK_KEY) != FORMAT:
            raise ValueError(f"it was made by a newer toolbox (format {data.get(PACK_KEY)!r})")
        entries = data.get("flows")
        if not isinstance(entries, list) or not entries:
            raise ValueError("it has no flows")
        flows = tuple(FlowStore.parse(str(entry["name"]), entry) for entry in entries)
        return cls(str(data.get("folder", "")), flows)

    def needs(self) -> list[str]:
        """Flows its boxes use that are not in it (their file names), A-Z: they must exist where it is imported."""
        own = {f.name for f in self.flows}
        used = {n.action.removeprefix(PREFIX) for f in self.flows for n in f.nodes if n.action.startswith(PREFIX)}
        return sorted(used - own)

    def renamed(self, names: dict[str, str]) -> "FlowPack":
        """The same flows under new file names (old → new); their boxes that run one of them follow."""
        actions = {PREFIX + old: PREFIX + new for old, new in names.items()}
        return FlowPack(self.folder, tuple(
            replace(f, name=names.get(f.name, f.name),
                    nodes=tuple(replace(n, action=actions.get(n.action, n.action)) for n in f.nodes))
            for f in self.flows))
