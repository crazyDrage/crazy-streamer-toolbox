from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.boxes.build_object import BuildObject
from streamer_toolbox.core.data.boxes.compare_objects import CompareObjects
from streamer_toolbox.core.data.boxes.get_from_object import GetFromObject
from streamer_toolbox.core.data.boxes.object_has_key import ObjectHasKey
from streamer_toolbox.core.data.boxes.object_keys import ObjectKeys
from streamer_toolbox.core.data.boxes.object_values import ObjectValues
from streamer_toolbox.core.data.boxes.remove_from_object import RemoveFromObject
from streamer_toolbox.core.data.boxes.set_in_object import SetInObject


class ObjectActions:
    """Object boxes (SAMMI's Object commands): read, change and build objects that come by wire or from a
    variable (${var.name}). Changing gives back a new object; store it with Set variable to keep it. Reading
    finds a key in any upper / lower case if there's no exact one. Compare objects tells what changed between two.
    A key may be a path: "right_arm.id" is the id inside right_arm, "outputs.0" the first of a list.

    One Box class per box, in boxes/."""

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (GetFromObject(), ObjectHasKey(), ObjectKeys(), ObjectValues(), SetInObject(),
                    RemoveFromObject(), BuildObject(), CompareObjects()):
            actions.add_box(box, "object")
