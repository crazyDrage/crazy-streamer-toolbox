from collections.abc import Callable, Mapping
from typing import Any

from nicegui import ui

from streamer_toolbox.connections.vtube_studio.vts_animation import VtsAnimation
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.interfaces.field_editor import FieldEditor
from streamer_toolbox.gui.components.flow_editor.animation_dialog import AnimationDialog
from streamer_toolbox.gui.components.flow_editor.animation_map import AnimationMap


class AnimationInput(FieldEditor):
    """A box's model animation field: what it holds in one line, a small map of the path, and Edit (its window).
    The animation is kept in the box itself (the flow file); the window can also save it to a file / load one."""

    def __init__(self, label: str, value: Any, actions: ActionRegistry, files: BoxValueFiles,
                 on_change: Callable[[Any], None], params: Mapping[str, Any] | None = None) -> None:
        self._label = label or "Animation"
        self._value = value
        self._actions = actions
        self._files = files
        self._on_change = on_change

    def build(self) -> None:
        with ui.column().classes("w-full gap-1"):
            ui.label(self._label).classes("text-sm font-semibold")
            self._summary()

    @staticmethod
    def text(value: Any) -> str:
        """What the box shows for it: "3 steps · 3 s · fixed spots"."""
        try:
            return summary(VtsAnimation.from_dict(value))
        except (TypeError, KeyError, ValueError):
            return "⚠ can't read it"

    @ui.refreshable_method
    def _summary(self) -> None:
        try:
            animation = VtsAnimation.from_dict(self._value)
        except (TypeError, KeyError, ValueError) as e:
            ui.label(f"⚠ can't read it ({e}); Edit starts a new one").classes("text-xs text-warning")
            animation = VtsAnimation()
        if animation.steps:
            ui.html(AnimationMap.svg(animation), sanitize=False).classes("w-full")
        ui.label(summary(animation)).classes("text-xs opacity-70")
        ui.button("Edit animation", icon="animation", on_click=lambda: AnimationDialog(
            animation, self._actions, self._files, self._saved).open()).props("no-caps outline dense")

    def _saved(self, animation: VtsAnimation) -> None:
        self._value = animation.to_dict()
        self._on_change(self._value)
        self._summary.refresh()


def summary(animation: VtsAnimation) -> str:
    """"3 steps · 2.5 s · from where the model is" / "No steps yet"."""
    if not animation.steps:
        return "No steps yet: Edit animation, then move the model in VTS and add its spots"
    count = len(animation.steps)
    where = "from where the model is" if animation.relative else "fixed spots"
    return f"{count} step{'s' if count > 1 else ''} · {animation.seconds:g} s · {where}"
