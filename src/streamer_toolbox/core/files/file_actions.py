from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.boxes.read_text_file import ReadTextFile
from streamer_toolbox.core.files.boxes.write_text_file import WriteTextFile


class FileActions:
    """Text file boxes, e.g. a counter an OBS text source shows (SAMMI's lizard_combo.txt). Flow only: they're
    not offered over the API or in the SAMMI deck, so no caller can write files on this PC.

    One Box class per box, in boxes/."""

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (WriteTextFile(), ReadTextFile()):
            actions.add_box(box, "file")
