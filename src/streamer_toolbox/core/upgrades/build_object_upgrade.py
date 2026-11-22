from dataclasses import replace
from typing import Any

from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.upgrades.settings_upgrade import SettingsUpgrade

BUILD, JOIN = "object.build", "object.join"
PAIRS = 5  # the old box had name_1 / value_1 ... name_5 / value_5
START = "start"


class BuildObjectUpgrade(SettingsUpgrade):
    """Settings version 8 (2026-11-22, docs/SETTINGS_CHANGES.md), his "Build object box needs an update. it
    should look more like the Input box, and adding variables. remove the start input, because we have a combine
    object box": Build object's five name + value pairs become lines he names (named_lines: {name: value}); an
    empty name is left out as before, a later pair with the same name wins as before.

    A box that had a start object gets a Join objects box (first = the start object, second = Build object), and
    everything that read Build object's result reads Join objects' instead: the flow gives the same object."""

    version = 8
    about = "Build object as lines"

    def __init__(self, flows: FlowLibrary) -> None:
        self._flows = flows

    def run(self) -> list[str]:
        said = []
        for flow in self._flows.all():
            changed = self.flow(flow)
            if changed != flow:
                self._flows.save(changed, flow.name)
                joined = len(changed.nodes) - len(flow.nodes)
                said.append(f"flow {flow.label!r}: Build object as lines"
                            + (f", {joined} start object(s) now a Join objects box" if joined else ""))
        return said

    def flow(self, flow: Flow) -> Flow:
        old = [node for node in flow.nodes if node.action == BUILD and _old_shape(node.params)]
        if not old:
            return flow
        nodes = list(flow.nodes)
        taken = {node.id for node in nodes}
        for build in old:
            start = build.params.get(START)
            at = nodes.index(next(node for node in nodes if node.id == build.id))
            nodes[at] = replace(build, params=_lines(build.params), outputs={})
            if start in (None, "", {}):
                continue
            join_id = _free_id(taken)
            taken.add(join_id)
            nodes = [replace(node, params=_point(node.params, build.id, join_id)) for node in nodes]
            x, y = build.box or (0.0, 0.0)
            nodes.append(FlowNode(join_id, JOIN, {"first": start, "second": f"${{box.{build.id}}}"},
                                  box=(x + 300.0, y)))
        return replace(flow, nodes=tuple(nodes))


def _old_shape(params: dict[str, Any]) -> bool:
    return START in params or any(f"{part}_{n}" in params for part in ("name", "value") for n in range(1, PAIRS + 1))


def _lines(params: dict[str, Any]) -> dict[str, Any]:
    lines: dict[str, Any] = {}
    for n in range(1, PAIRS + 1):
        name = str(params.get(f"name_{n}") or "").strip()
        if name:
            lines.pop(name, None)  # a later pair with the same name wins, and its line comes last
            lines[name] = params.get(f"value_{n}", "")
    return lines


def _point(value: Any, old: str, new: str) -> Any:
    """`value` with every reference to box `old`'s result (${box.old}, ${box.old.key}) pointing at `new`."""
    if isinstance(value, str):
        return value.replace(f"${{box.{old}}}", f"${{box.{new}}}").replace(f"${{box.{old}.", f"${{box.{new}.")
    if isinstance(value, dict):
        return {key: _point(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_point(item, old, new) for item in value]
    return value


def _free_id(taken: set[str]) -> str:
    number = 1
    while f"n{number}" in taken:
        number += 1
    return f"n{number}"
