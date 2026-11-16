from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.cache.boxes.remembered_value import RememberedValue
from streamer_toolbox.core.cache.remembered_values import RememberedValues


class RememberedActions:
    """Boxes for values kept a while (RememberedValues): Remembered value. One Box class per box, in boxes/."""

    def __init__(self, values: RememberedValues) -> None:
        self._values = values

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (RememberedValue(self._values),):
            actions.add_box(box, "cache")
