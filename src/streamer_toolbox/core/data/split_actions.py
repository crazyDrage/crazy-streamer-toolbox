from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.box_value import to_kind, understand


class SplitActions:
    """Split data: takes an object (a position, JSON text, ...) and gives each field on its own output, as the
    kind it was set to (number, text, yes/no, list, object). The editor finds the fields and kinds by itself."""

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("data.split", self.split, "Takes an object (e.g. from Get model position) apart: one output "
                    "per field, each as its kind (number, text, ...). Wire its outputs into other boxes' fields",
                    "Split data", group="Split", flow_only=True, data_outputs="fields")

    @staticmethod
    async def split(data: Any, fields: dict[str, str] | None = None) -> dict[str, Any]:
        whole = understand(data)
        if not isinstance(whole, dict):
            raise ValueError(f"Split data needs an object with fields, got {data!r}")
        if not fields:
            return dict(whole)
        missing = [name for name in fields if name not in whole]
        if missing:
            raise KeyError(f"the data has no field {', '.join(missing)} (it has {', '.join(whole) or 'none'})")
        return {name: to_kind(whole[name], kind) for name, kind in fields.items()}
