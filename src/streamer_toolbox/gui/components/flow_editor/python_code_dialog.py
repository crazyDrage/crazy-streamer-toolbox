from collections.abc import Mapping
from pathlib import Path
from typing import Any

from nicegui import app, ui

from streamer_toolbox.core.system.boxes.run_python import RunPython
from streamer_toolbox.core.system.python_syntax import syntax_problem


class PythonCodeDialog:
    """Run Python's code window: the file's code to change and Save. A file that isn't there yet starts as the
    template for the box's values (its inputs and outputs) and is written at the first Save. Save checks the
    writing first and says the line of a mistake, but saves anyway (half-done code is fine to keep)."""

    def __init__(self, path: Path, box: RunPython, params: Mapping[str, Any]) -> None:
        self._path = path
        self._box = box
        self._params = params
        self._saved = ""
        self._leaving = False  # Close pressed once with changes not saved

    def open(self) -> None:
        new = not self._path.is_file()
        text = self._box.template(self._params) if new else self._path.read_text(encoding="utf-8")
        self._saved = "" if new else text
        dark = app.storage.general.get("theme", "dark") != "light"
        with ui.dialog().props("persistent maximized") as self._dialog, \
                ui.card().classes("w-full h-full gap-2 no-wrap"):
            with ui.row().classes("items-center no-wrap w-full"):
                ui.label("Edit code").classes("text-lg font-semibold flex-1")
                ui.button(icon="close", on_click=self._close).props("flat round dense").tooltip("Close")
            ui.label(str(self._path)).classes("text-xs opacity-70 break-all")
            self._new = ui.label("New file: it is made when you press Save (or when the box runs).") \
                .classes("text-xs text-warning")
            self._new.set_visibility(new)
            self._code = ui.codemirror(text, language="Python", theme="vscodeDark" if dark else "vscodeLight",
                                       line_wrapping=True,  # long lines stay readable on the phone
                                       on_change=lambda _: self._changed()).classes("w-full grow min-h-0")
            self._problem = ui.label("").classes("text-sm text-negative")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Close", on_click=self._close).props("no-caps flat")
                ui.button("Save", icon="save", on_click=self._save).props("no-caps unelevated")
        self._dialog.open()

    def _changed(self) -> None:
        self._leaving = False

    def _save(self) -> None:
        text = self._code.value
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(text, encoding="utf-8")
        self._saved = text
        self._new.set_visibility(False)
        problem = syntax_problem(text)
        self._problem.set_text(f"Saved, but Python can't read it: {problem}" if problem else "")
        ui.notify("Saved: the box uses it at its next run", type="warning" if problem else "positive")

    def _close(self) -> None:
        if self._code.value != self._saved and not self._leaving:
            self._leaving = True
            ui.notify("Not saved yet: Save, or press Close again to leave it as it was", type="warning")
            return
        self._dialog.close()
