from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.variables.boxes.add_to_viewer_value import AddToViewerValue
from streamer_toolbox.core.variables.boxes.get_viewer_value import GetViewerValue
from streamer_toolbox.core.variables.boxes.set_viewer_value import SetViewerValue
from streamer_toolbox.core.variables.boxes.top_viewers import TopViewers
from streamer_toolbox.core.variables.variable_store import VariableStore


class ViewerActions:
    """Values per viewer (e.g. how often someone lurked): one variable holds {viewer: value}. The viewer is
    usually Start's user_login; names are kept in lower case so "VexFan" and "vexfan" are one viewer.

    One Box class per box, in boxes/."""

    def __init__(self, variables: VariableStore) -> None:
        self._variables = variables

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (GetViewerValue(self._variables), SetViewerValue(self._variables),
                    AddToViewerValue(self._variables), TopViewers(self._variables)):
            actions.add_box(box, "viewer")
