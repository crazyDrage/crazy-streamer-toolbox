from streamer_toolbox.gui.components.flow_editor.animation_input import AnimationInput
from streamer_toolbox.gui.components.flow_editor.placement_input import PlacementInput

from streamer_toolbox.core.interfaces.field_editor import FieldEditor

# a field whose value the box keeps itself and edits in its own window (RegisteredAction.editors): kind → its input.
# Plugins add theirs under "<plugin id>.<kind>" (PluginContext.add_field_editor)
EDITORS: dict[str, type[FieldEditor]] = {"vts_animation": AnimationInput, "obs_placement": PlacementInput}


def add_editor(kind: str, editor: type[FieldEditor]) -> None:
    if kind in EDITORS:
        raise ValueError(f"there is a field editor {kind!r} already")
    EDITORS[kind] = editor
