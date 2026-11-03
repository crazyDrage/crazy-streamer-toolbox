from abc import ABC, abstractmethod
from typing import Any


class FieldEditor(ABC):
    """A field whose value the box keeps itself and edits in its own window (RegisteredAction.editors: field →
    kind), like the VTube Studio animation or the OBS place. The flow editor makes one per field it shows:
    Editor(label, value, actions, files, on_change, params), with the field's label, its value, the action
    registry, the BoxValueFiles for saving to / loading from files, on_change(new value) to call when it
    changes, and the box's other values. A plugin adds its own with ctx.add(TheEditorClass): the class, not
    one of it, with `kind` set; a box names it in editors={field: "<plugin id>.<kind>"}."""

    kind: str = ""

    @abstractmethod
    def build(self) -> None:
        """Draws it in the box form (NiceGUI), e.g. a one-line summary and a button that opens its window."""

    @staticmethod
    @abstractmethod
    def text(value: Any) -> str:
        """The value in short, for the box's row on the canvas and its one-line summary ("3 steps · 2.5 s")."""
