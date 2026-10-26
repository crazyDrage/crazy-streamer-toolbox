import re
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from streamer_toolbox.core.flows.flow import Flow



class VariableRenamer:
    """Renames a variable inside a flow, everywhere a flow can use one: ${var.old} and ${var.old.field} (also
    inside longer text), "save result in variable", and the fields that take a variable's name (`fields`: a box's
    action → its RegisteredAction.variable_fields)."""

    def __init__(self, old: str, new: str, fields: Callable[[str], tuple[str, ...]] = lambda action: ()) -> None:
        self._fields = fields
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
        if key in self._fields(action) and value == self._old:
            return self._new
        if isinstance(value, str):
            return self._pattern.sub("${var." + self._new, value)
        if isinstance(value, dict):  # a Value box's lines
            return {k: self._value(action, "", v) for k, v in value.items()}
        return value
