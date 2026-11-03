from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.interfaces.import_target import ImportTarget
from streamer_toolbox.core.interfaces.importer import Importer


class ImportTool:
    """Overlay → Import (his round 64): a card per importer, the toolbox's own (StreamElements) and the ones
    plugins add (ctx.add(Importer)). What they bring goes to Overlay → Widgets."""

    def __init__(self, importers: Callable[[], list[Importer]], target: ImportTarget) -> None:
        self._importers = importers  # asked each time: a plugin switched off leaves its importer out
        self._target = target

    def build(self) -> None:
        importers = self._importers()
        if not importers:
            ui.label("No importers.").classes("opacity-70")
        for importer in importers:
            with ui.card().classes("w-full gap-2"):
                with ui.row().classes("items-center gap-2 no-wrap"):
                    ui.icon(importer.icon).classes("text-2xl text-primary")
                    with ui.column().classes("gap-0"):
                        ui.label(importer.title).classes("text-lg font-semibold")
                        if importer.description:
                            ui.label(importer.description).classes("text-xs opacity-70")
                try:
                    importer.build(self._target)
                except Exception as e:  # a plugin's broken card doesn't take the page down
                    ui.label(f"This importer failed to draw: {e}").classes("text-sm text-negative")
