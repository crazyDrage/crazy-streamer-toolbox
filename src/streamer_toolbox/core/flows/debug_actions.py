from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.flows.boxes.debug import Debug, Show

DEBUG_BOX = "logic.debug"


class DebugActions:
    """The Debug box (core/flows/boxes/debug.py): takes a value, shows it and gives it on unchanged."""

    def __init__(self, show: Show | None = None) -> None:
        self._show = show

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add_box(Debug(self._show), DEBUG_BOX.split(".")[0])
