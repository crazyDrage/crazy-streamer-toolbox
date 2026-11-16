from nicegui import ui


async def sure_to_delete(question: str, detail: str) -> bool:
    """A yes/no before deleting, on this screen only (the ConfirmService asks on every open screen): the Flows
    page and the Edit flow page."""
    with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-4"):
        ui.label(question).classes("text-lg font-semibold")
        ui.label(detail).classes("text-sm opacity-80")
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("no-caps flat")
            ui.button("Delete", icon="delete", on_click=lambda: dialog.submit(True)) \
                .props("no-caps unelevated color=negative")
    result = await dialog
    dialog.delete()
    return bool(result)
