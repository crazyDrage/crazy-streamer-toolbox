import logging
import re
import tomllib
from pathlib import Path
from typing import Any

import tomlkit

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import DONE, START, FlowWire
from streamer_toolbox.core.flows.old_end_boxes import end_boxes_from_lines
from streamer_toolbox.core.flows.old_split_boxes import split_boxes_away
from streamer_toolbox.core.flows.old_start_box import start_boxes_from_triggers
from streamer_toolbox.core.flows.old_value_boxes import lines_from_old_values

log = logging.getLogger(__name__)
NAME = re.compile(r"[a-z0-9_]+")
TRIGGER_OWN = ("kind", "id", "box")  # a trigger's keys in the file that aren't what it matches


class FlowStore:
    """Flows as files: <folder>/<name>.toml, one flow each (label, description, [[inputs]], [[nodes]], [[wires]],
    [[triggers]] each with the id of its Start box). The same class keeps the templates, in their own folder.

    Older files with a [[steps]] list are read as a chain of boxes and written back as nodes and wires; a Value
    box with one value gets it as its one line (old_value_boxes); a Split data box is wired around and goes
    (old_split_boxes); triggers without an id get their own Start box (old_start_box).
    """

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def all(self) -> list[Flow]:
        flows = [self.read(path.stem) for path in sorted(self.folder.glob("*.toml"))]
        return [flow for flow in flows if flow is not None]

    def read(self, name: str) -> Flow | None:
        """One flow from its file; None (and a line in the log) when the file is broken or gone."""
        path = self.path_of(name)
        try:
            return self.parse(name, tomllib.loads(path.read_text(encoding="utf-8")))
        except Exception as e:  # one broken file mustn't hide the others
            log.error("flow %s not loaded: %s", path.name, e)
            return None

    def stamps(self) -> dict[str, int]:
        """Each file's name → when it was last changed (ns): what changed since is read again (FlowLibrary.reload)."""
        stamps = {}
        for path in self.folder.glob("*.toml"):
            try:
                stamps[path.stem] = path.stat().st_mtime_ns
            except OSError:  # deleted in between
                pass
        return stamps

    def path_of(self, name: str) -> Path:
        return self.folder / f"{name}.toml"

    def exists(self, name: str) -> bool:
        return self.path_of(name).exists()

    def save(self, flow: Flow) -> None:
        if not NAME.fullmatch(flow.name):
            raise ValueError(f"flow name {flow.name!r}: use only a-z, 0-9 and _")
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path_of(flow.name).write_text(tomlkit.dumps(self.to_data(flow)), encoding="utf-8")

    def delete(self, name: str) -> None:
        self.path_of(name).unlink(missing_ok=True)

    @staticmethod
    def parse(name: str, data: dict[str, Any]) -> Flow:
        if "steps" in data and "nodes" not in data:
            nodes, wires = _from_steps(data["steps"])
        else:
            nodes = tuple(_node(n["id"], n) for n in data.get("nodes", []))
            wires = tuple(FlowWire(w["from"], w.get("port", DONE), w["to"], w.get("entry", ""))
                          for w in data.get("wires", []))
        nodes, wires = split_boxes_away(*end_boxes_from_lines(lines_from_old_values(nodes), wires))
        triggers = tuple(FlowTrigger(t["kind"], {k: v for k, v in t.items() if k not in TRIGGER_OWN},
                                     str(t.get("id", "")), _spot(t))
                         for t in data.get("triggers", []))
        inputs = tuple(FlowInput(i["name"], i.get("default"), i.get("description", ""))
                       for i in data.get("inputs", []))
        nodes, wires, triggers = start_boxes_from_triggers(nodes, wires, triggers, inputs)
        return Flow(name, data.get("label", name.replace("_", " ").capitalize()), nodes, wires, triggers,
                    data.get("description", ""), inputs, data.get("when_busy", "alongside"),
                    float(data.get("cooldown", 0)), float(data.get("user_cooldown", 0)),
                    bool(data.get("refund_on_fail", False)), str(data.get("folder", "")).strip(),
                    bool(data.get("enabled", True)), bool(data.get("triggers_enabled", True)),
                    bool(data.get("as_box", True)), _spot(data, "start_box"), _spot(data, "input_box"))

    @staticmethod
    def to_data(flow: Flow) -> dict[str, Any]:
        data: dict[str, Any] = {"label": flow.label}
        if flow.folder:
            data["folder"] = flow.folder
        for key in ("enabled", "triggers_enabled", "as_box"):  # only said when switched off
            if not getattr(flow, key):
                data[key] = False
        if flow.description:
            data["description"] = flow.description
        if flow.when_busy != "alongside":
            data["when_busy"] = flow.when_busy
        for key in ("cooldown", "user_cooldown"):
            if getattr(flow, key):
                data[key] = getattr(flow, key)
        if flow.refund_on_fail:
            data["refund_on_fail"] = True
        if flow.inputs:
            data["inputs"] = [{"name": i.name, **({} if i.default is None else {"default": i.default}),
                               **({"description": i.description} if i.description else {})} for i in flow.inputs]
        if flow.triggers:
            data["triggers"] = [{"kind": t.kind, **({"id": t.id} if t.id else {}), **t.match,
                                 **({"box": _rounded(t.box)} if t.box is not None else {})} for t in flow.triggers]
        for key in ("start_box", "input_box"):
            if getattr(flow, key) is not None:
                data[key] = _rounded(getattr(flow, key))
        nodes = []
        for node in flow.nodes:
            entry: dict[str, Any] = {"id": node.id, "action": node.action, "params": _inline(node.params)}
            if not node.enabled:
                entry["enabled"] = False
            if node.save_as:
                entry["save_as"] = node.save_as
            if node.note:
                entry["note"] = node.note
            if node.box is not None:
                entry["box"] = _rounded(node.box)
            if node.outputs:
                entry["outputs"] = _inline(node.outputs)
            nodes.append(entry)
        data["nodes"] = nodes
        wires = tomlkit.array()
        wires.extend(_inline({"from": w.source, "port": w.port, "to": w.target}
                             | ({"entry": w.entry} if w.entry else {}))
                     for w in flow.wires)
        data["wires"] = wires.multiline(True)
        return data


def _spot(data: dict[str, Any], key: str = "box") -> tuple[float, float] | None:
    return tuple(data[key]) if key in data else None


def _rounded(spot: tuple[float, float]) -> list[int]:
    return [round(spot[0]), round(spot[1])]


def _node(node_id: str, n: dict[str, Any]) -> FlowNode:
    return FlowNode(node_id, n["action"], dict(n.get("params", {})), bool(n.get("enabled", True)),
                    n.get("note", ""), n.get("save_as", ""), tuple(n["box"]) if "box" in n else None,
                    {str(k): str(v) for k, v in dict(n.get("outputs", {})).items()})


def _from_steps(steps: list[dict[str, Any]]) -> tuple[tuple[FlowNode, ...], tuple[FlowWire, ...]]:
    nodes = tuple(_node(f"n{i}", s) for i, s in enumerate(steps, 1))
    wires, previous, port = [], START, "out"
    for node in nodes:
        wires.append(FlowWire(previous, port, node.id))
        previous, port = node.id, DONE
    return nodes, tuple(wires)


def _inline(values: dict[str, Any]) -> Any:
    table = tomlkit.inline_table()
    table.update(values)
    return table
