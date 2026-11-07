from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.widgets.design_preset import PRESETS, DesignPreset


class DesignAddList:
    """The widget editor's list of what can be added (his round 85: on the left side, in a list), in groups:
    plain pieces, the alert's own values (in an alert layer), live values, goal bars and recent names. A click
    puts it in the middle of the canvas, in the layer being edited."""

    def __init__(self, alert: bool, add: Callable[[DesignPreset], None]) -> None:
        self._alert = alert
        self._add = add

    def build(self) -> None:
        ui.label("Add").classes("text-sm font-semibold")
        group = ""
        for preset in PRESETS:
            if not preset.fits(self._alert):
                continue
            if preset.group != group:
                group = preset.group
                ui.label(group).classes("text-xs font-semibold uppercase tracking-wider text-primary pt-2")
            with ui.row().classes("w-full items-center no-wrap gap-2 rounded px-1 py-0.5 cursor-pointer "
                                  "hover:bg-gray-500/10") \
                    .on("click", lambda p=preset: self._add(p)):
                ui.icon(preset.icon, size="xs").classes("opacity-70")
                ui.label(preset.title).classes("flex-1 min-w-0 truncate text-sm")
