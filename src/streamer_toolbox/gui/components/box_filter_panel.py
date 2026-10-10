from nicegui import ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.box_filter import BoxFilter
from streamer_toolbox.core.actions.box_filter_store import BASIC_FILTERS, BoxFilterStore
from streamer_toolbox.gui.components.box_filter_dialog import BoxFilterDialog
from streamer_toolbox.gui.components.flow_editor.action_catalog import ActionCatalog


class BoxFilterPanel:
    """Settings → Box filters: his own filters for the Add box window, next to the basic ones that are always
    there. New / edit opens BoxFilterDialog (every box left, the filter's boxes right); saved at once."""

    def __init__(self, filters: BoxFilterStore, actions: ActionRegistry) -> None:
        self._filters = filters
        self._actions = actions

    def build(self) -> None:
        ui.label("Box filters").classes("text-lg font-semibold")
        ui.label("Short lists for the Add box window (its Show list): only the boxes you put in. Used from the "
                 "next time the window opens.").classes("text-sm opacity-80")
        self._rows()
        ui.button("New filter", icon="add", on_click=lambda: self._edit(None)).props("no-caps outline dense")

    @ui.refreshable_method
    def _rows(self) -> None:
        with ui.column().classes("w-full gap-1"):
            for box_filter in self._filters.custom():
                with ui.row().classes("items-center no-wrap w-full gap-2"):
                    with ui.column().classes("gap-0 flex-1 min-w-0"):
                        ui.label(box_filter.name).classes("font-medium")
                        ui.label(self._summary(box_filter)).classes("text-xs opacity-70")
                    ui.button(icon="edit", on_click=lambda f=box_filter: self._edit(f)).props("flat round dense")
                    ui.button(icon="delete", on_click=lambda f=box_filter: self._delete(f)).props("flat round dense")
            ui.label("Always there: " + ", ".join(f.name for f in BASIC_FILTERS)).classes("text-xs opacity-60")

    def _summary(self, box_filter: BoxFilter) -> str:
        """"12 boxes: OBS 7, Sound 2, Logic 3"."""
        inside = ActionCatalog(self._actions, box_filter=box_filter).categories()
        total = sum(count for _, _, count in inside)
        parts = ", ".join(f"{title} {count}" for _, title, count in inside)
        return f"{total} box{'' if total == 1 else 'es'}: {parts}"

    async def _edit(self, old: BoxFilter | None) -> None:
        if await BoxFilterDialog(self._filters, self._actions, old).open():
            self._rows.refresh()

    def _delete(self, box_filter: BoxFilter) -> None:
        self._filters.delete(box_filter.name)
        self._rows.refresh()
        ui.notify(f"Filter {box_filter.name!r} deleted")
