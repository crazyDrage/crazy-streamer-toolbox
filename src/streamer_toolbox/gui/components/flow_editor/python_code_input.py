from collections.abc import Callable, Mapping
from typing import Any

from nicegui import ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.files.box_value_files import BoxValueFiles
from streamer_toolbox.core.interfaces.field_editor import FieldEditor
from streamer_toolbox.core.system.boxes.run_python import RunPython
from streamer_toolbox.gui.components.file_dialog import FileDialog
from streamer_toolbox.gui.components.flow_editor.python_code_dialog import PythonCodeDialog

HINT = RunPython.hints["file"]


class PythonCodeInput(FieldEditor):
    """Run Python's file field (his answer of 10-30: "you can add that"): the name or path as before, its file
    button, and Edit code, which opens the file in a code window (also from the phone). The field keeps only
    the name or path; the code stays in the file."""

    def __init__(self, label: str, value: Any, actions: ActionRegistry, files: BoxValueFiles,
                 on_change: Callable[[Any], None], params: Mapping[str, Any] | None = None) -> None:
        self._label = label or "File"
        self._value = value if isinstance(value, str) else ""
        self._box = RunPython(files.folder("python"))
        self._on_change = on_change
        self._params = params or {}

    def build(self) -> None:
        with ui.column().classes("w-full gap-1"):
            ui.label(self._label).classes("text-sm font-semibold")
            ui.label(HINT).classes("text-xs opacity-70")
            with ui.row().classes("w-full items-center no-wrap gap-1"):
                self._input = ui.input(value=self._value, placeholder="e.g. lizard",
                                       on_change=lambda e: self._set(e.value or "")).classes("grow")
                ui.button(icon="folder_open", on_click=self._pick).props("flat round dense") \
                    .tooltip("Pick a .py file on this PC")
            ui.button("Edit code", icon="code", on_click=self._edit).props("no-caps outline dense")

    @staticmethod
    def text(value: Any) -> str:
        return str(value or "")

    def _set(self, value: str) -> None:
        self._value = value.strip()
        self._on_change(self._value)

    async def _pick(self) -> None:
        path = await FileDialog((".py",)).open(self._value)
        if path:
            self._input.set_value(path)

    def _edit(self) -> None:
        if "${" in self._value:
            ui.notify("The file comes from a wire or a variable here: only a typed name or path can be edited",
                      type="warning")
            return
        try:
            path = self._box.path(self._value)
        except ValueError as e:
            ui.notify(str(e), type="warning")
            return
        PythonCodeDialog(path, self._box, self._params).open()
