import json
from typing import Any

from nicegui import ui

from streamer_toolbox.core.data.box_value import kind_of

LONG = 600  # characters a box shows on the canvas in debug mode


class ResultView:
    """What a box gave, readable: its kind (text, number, yes/no, list, object) and the value exactly, text in
    quotes so spaces and the full name show ("CrazyDrage Human (Ready to Rig)", not just "Human"). An object also
    gets one line per field, each with its kind: those are what its orange dots and the helpers (@keys, ...) give."""

    @staticmethod
    def text(value: Any, limit: int = LONG) -> str:
        """The value on a few lines, for a box on the canvas."""
        if value is None:
            return "nothing (no result)"
        shown = json.dumps(value, ensure_ascii=False, indent=1, default=str)
        if len(shown) > limit:
            shown = shown[:limit] + " …"
        return f"{kind_of(value)}: {shown}"

    @staticmethod
    def show(value: Any) -> None:
        """The value in the box panel."""
        if value is None:
            ui.label("It gave nothing (a box that only does something).").classes("text-xs opacity-70")
            return
        ui.label(f"kind: {kind_of(value)}").classes("text-xs font-semibold")
        shown = json.dumps(value, ensure_ascii=False, indent=2, default=str)
        ui.code(shown, language="json").classes("w-full text-xs max-h-60 overflow-auto")
        if isinstance(value, dict):
            with ui.column().classes("gap-0 w-full"):
                for key, item in value.items():
                    with ui.row().classes("no-wrap gap-2 w-full text-xs"):
                        ui.label(key).classes("font-semibold shrink-0")
                        ui.label(kind_of(item)).classes("opacity-60 shrink-0")
                        ui.label(json.dumps(item, ensure_ascii=False, default=str)[:120]) \
                            .classes("break-all min-w-0")
