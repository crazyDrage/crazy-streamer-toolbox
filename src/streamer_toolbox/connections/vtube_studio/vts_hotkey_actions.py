from streamer_toolbox.connections.vtube_studio.boxes.trigger_hotkey import TriggerHotkey
from streamer_toolbox.connections.vtube_studio.boxes.vts_hotkey_box import Request
from streamer_toolbox.core.actions.action_registry import ActionRegistry


class VtsHotkeyActions:
    """VTube Studio's hotkeys of the loaded model: list them and fire one by name or id.

    One Box class per box, in boxes/."""

    def __init__(self, request: Request) -> None:
        self._request = request

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (TriggerHotkey(self._request),):
            actions.add_box(box, "vts")
