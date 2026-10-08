from collections.abc import Callable, Mapping
from typing import Any

from nicegui import ui

from streamer_toolbox.connections.obs.obs_placement import ObsPlacement
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.gui.components.flow_editor.placement_dialog import PlacementDialog


class PlacementInput:
    """A box's place field: where it is in one line, Set up the place (its window, with a marker in OBS) and
    Clear. The place is kept in the box itself (the flow file). The window starts in the box's own scene."""

    def __init__(self, label: str, value: Any, actions: ActionRegistry, files: BoxValueFiles,
                 on_change: Callable[[Any], None], params: Mapping[str, Any] | None = None) -> None:
        self._label = label or "Place"
        self._params = params or {}  # the box's values: its scene is where the marker goes
        self._value = value
        self._actions = actions
        self._on_change = on_change

    def build(self) -> None:
        with ui.column().classes("w-full gap-1"):
            ui.label(self._label).classes("text-sm font-semibold")
            self._summary()

    @staticmethod
    def text(value: Any) -> str:
        """What the box shows for it: "x 1600, y 50 · 320 × 180"."""
        try:
            return ObsPlacement.from_value(value).text()
        except ValueError:
            return "⚠ can't read it"

    @ui.refreshable_method
    def _summary(self) -> None:
        place = None
        if self._value not in (None, ""):
            try:
                place = ObsPlacement.from_value(self._value)
            except ValueError:
                ui.label("⚠ can't read it; Set up the place starts a new one").classes("text-xs text-warning")
        ui.label(place.text() if place else "Not set up yet: a marker in OBS shows where it goes") \
            .classes("text-xs opacity-70")
        with ui.row().classes("gap-2"):
            ui.button("Set up the place", icon="crop_free",
                      on_click=lambda: PlacementDialog(place, self._actions, self._saved, self._scene()).open()) \
                .props("no-caps outline dense")
            if place:
                ui.button("Clear", on_click=lambda: self._set("")).props("no-caps flat dense")

    def _scene(self) -> str:
        """The box's own scene, if it's typed (not a variable or a wire)."""
        scene = self._params.get("scene", "")
        return scene if isinstance(scene, str) and "${" not in scene else ""

    def _saved(self, place: ObsPlacement) -> None:
        self._set(place.to_dict())

    def _set(self, value: Any) -> None:
        self._value = value
        self._on_change(value)
        self._summary.refresh()
