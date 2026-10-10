import re
from dataclasses import replace
from typing import Any

from streamer_toolbox.core.flows.flow import Flow

# box fields that hold a variable's name itself (not ${var.x}): Set / Add to variable, Set field, For each, lists
NAME_FIELDS = {("var.set", "name"), ("var.add", "name"), ("var.set_field", "name"), ("logic.for_each", "item"),
               ("list.add", "name"), ("list.remove", "name")}


class VariableRenamer:
    """Renames a variable inside a flow, everywhere a flow can use one: ${var.old} and ${var.old.field} (also
    inside longer text), "save result in variable", and the fields that take a variable's name."""

    def __init__(self, old: str, new: str) -> None:
        self._old = old
        self._new = new
        self._pattern = re.compile(r"\$\{var\." + re.escape(old) + r"(?=[.}])")

    def flow(self, flow: Flow) -> Flow | None:
        """The flow with the new name, or None if it doesn't use the variable."""
        nodes, changed = [], False
        for node in flow.nodes:
            params = {k: self._value(node.action, k, v) for k, v in node.params.items()}
            save_as = self._new if node.save_as == self._old else node.save_as
            if params != node.params or save_as != node.save_as:
                changed = True
                node = replace(node, params=params, save_as=save_as)
            nodes.append(node)
        return replace(flow, nodes=tuple(nodes)) if changed else None

    def _value(self, action: str, key: str, value: Any) -> Any:
        if (action, key) in NAME_FIELDS and value == self._old:
            return self._new
        if isinstance(value, str):
            return self._pattern.sub("${var." + self._new, value)
        return value
