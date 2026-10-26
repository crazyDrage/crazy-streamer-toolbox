from streamer_toolbox.connections.tits.boxes.activate_trigger import ActivateTrigger
from streamer_toolbox.connections.tits.boxes.get_tits_item import GetTITSItem
from streamer_toolbox.connections.tits.boxes.get_tits_items import GetTITSItems
from streamer_toolbox.connections.tits.boxes.get_tits_triggers import GetTITSTriggers
from streamer_toolbox.connections.tits.boxes.throw_item import ThrowItem
from streamer_toolbox.connections.tits.boxes.tits_box import Ask
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class TitsActions:
    """T.I.T.S.' boxes, all its API has: throw items at the model, activate a trigger, and read what is there
    (the items, one item with its picture, the triggers). Items and triggers are picked by name (the pickers
    list them from the running program); the id is looked up.

    One Box class per box, in boxes/."""

    def __init__(self, ask: Ask) -> None:
        self._ask = ask

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (ThrowItem(self._ask), ActivateTrigger(self._ask), GetTITSItems(self._ask),
                    GetTITSItem(self._ask), GetTITSTriggers(self._ask)):
            actions.add_box(box, "tits")
