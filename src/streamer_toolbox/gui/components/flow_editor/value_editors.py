from streamer_toolbox.gui.components.flow_editor.animation_input import AnimationInput
from streamer_toolbox.gui.components.flow_editor.placement_input import PlacementInput

# a field whose value the box keeps itself and edits in its own window (RegisteredAction.editors): kind → its input
EDITORS = {"vts_animation": AnimationInput, "obs_placement": PlacementInput}
