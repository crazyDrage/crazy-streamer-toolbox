from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.data.boxes.json_text_to_value import JsonTextToValue
from streamer_toolbox.core.data.boxes.value_to_json_text import ValueToJsonText


class JsonActions:
    """JSON boxes: text from a file or a web answer into a value (list / object) and back, e.g. to keep a list
    in a file with the Text file boxes (SAMMI's vts_saves.json).

    One Box class per box, in boxes/."""

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (JsonTextToValue(), ValueToJsonText()):
            actions.add_box(box, "json")
