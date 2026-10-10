from nicegui import ui


class CopyFilesQuestion:
    """The window before files are copied from StreamElements (or another server) to this PC: says what is
    copied and that it is his to check whether he may. StreamElements' terms call the content on their service
    theirs or their licensors' and don't allow copying it out; what a user uploaded stays the user's."""

    def __init__(self, title: str, go: str = "I may use them: import") -> None:
        self._title = title
        self._go = go

    async def ask(self) -> bool:
        """True = he says he may and wants it. Call it where a window may be opened (not inside a part of the
        page that redraws by itself)."""
        with ui.dialog() as dialog, ui.card().classes("w-[34rem] max-w-full gap-3"):
            ui.label(self._title).classes("text-lg font-semibold")
            ui.label("Everything the widget needs is copied to this PC: its code, and the pictures, sounds, "
                     "videos, fonts and helper scripts it loads from StreamElements or other servers. It then "
                     "runs from this PC, without StreamElements being asked.").classes("text-sm opacity-80")
            with ui.row().classes("items-start no-wrap gap-2"):
                ui.icon("warning", color="warning", size="sm")
                with ui.column().classes("gap-1"):
                    ui.label("Make sure you are allowed to copy them.").classes("text-sm font-semibold")
                    ui.label("Files you made or uploaded yourself are yours. Files from StreamElements' own "
                             "library, or from an overlay or theme someone else made or sold, belong to them: "
                             "StreamElements' terms allow using their content on StreamElements only, and a "
                             "creator's licence may say the same. The toolbox can't check this for you.") \
                        .classes("text-sm opacity-80")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button(self._go, icon="download", on_click=lambda: dialog.submit(True)) \
                    .props("unelevated no-caps")
        sure = await dialog
        dialog.delete()
        return bool(sure)
