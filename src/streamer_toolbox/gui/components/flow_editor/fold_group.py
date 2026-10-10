from nicegui import ui

OPEN, CLOSED = "expand_more", "chevron_right"


class FoldGroup:
    """A sub group's heading in the Add box and Add trigger windows, with the list below it: the name in the
    toolbox's colour, how many it holds, and a click on it closes or opens the list. Put the list's rows into
    `body`: `with FoldGroup("Look", 3).body: ...`."""

    def __init__(self, title: str, count: int) -> None:
        with ui.row().classes("w-full no-wrap items-center gap-1 mt-2 px-1 py-1 rounded cursor-pointer "
                              "select-none hover:bg-gray-500/10") as head:
            self._arrow = ui.icon(OPEN).classes("text-lg text-primary")
            ui.label(title).classes("text-sm font-bold text-primary")
            ui.label(str(count)).classes("text-xs opacity-60 pl-1")
        self.body = ui.column().classes("w-full gap-0")
        head.on("click", self._flip)

    def _flip(self) -> None:
        self.body.set_visibility(not self.body.visible)
        self._arrow.set_name(OPEN if self.body.visible else CLOSED)
