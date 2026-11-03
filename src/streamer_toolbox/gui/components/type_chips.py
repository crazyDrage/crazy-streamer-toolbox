from collections import Counter
from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.plugins.plugin_types import plugin_types, type_label, type_order


class TypeChips:
    """A chip per plugin type, with how many plugins have it; a tap shows only those, a second tap all again
    (his ask of 2026-11-02: "make it sort-able ... because it could be hard if we have a lot of plugins"). On
    Get plugins and on the Plugins overview. `changed` redraws what the chips sort."""

    def __init__(self, changed: Callable[[], None]) -> None:
        self._changed = changed
        self.picked: str | None = None  # None: all

    def build(self, plugins_types: list[tuple[str, ...]]) -> None:
        """The chips for these plugins (each one's types); none when they are all of one type."""
        counts = Counter(t for types in plugins_types for t in plugin_types(types))
        if len(counts) < 2:
            self.picked = None
            return
        with ui.row().classes("items-center gap-1 w-full"):
            self._chip(None, "All", len(plugins_types))
            for type_id in type_order(counts):
                self._chip(type_id, type_label(type_id), counts[type_id])

    def fits(self, types: tuple[str, ...]) -> bool:
        return self.picked is None or self.picked in plugin_types(types)

    @staticmethod
    def badges(types: tuple[str, ...]) -> None:
        """A plugin's own types, small, on its card."""
        if types:
            with ui.row().classes("gap-1"):
                for type_id in plugin_types(types):
                    ui.badge(type_label(type_id)).props("outline color=primary")

    def _chip(self, type_id: str | None, label: str, count: int) -> None:
        ui.button(f"{label} ({count})", on_click=lambda: self._pick(type_id)) \
            .props(f"rounded no-caps padding='4px 12px' {'unelevated' if self.picked == type_id else 'outline'}") \
            .classes("text-sm")

    def _pick(self, type_id: str | None) -> None:
        self.picked = None if self.picked == type_id else type_id
        self._changed()
