from nicegui import ui

from streamer_toolbox.gui.components.debug_list import DebugList, look_of
from streamer_toolbox.gui.services.message_entry import MessageEntry
from streamer_toolbox.gui.services.message_log import MessageLog

POP_OUT = "window.open('/debug', 'tb-debug', 'width=520,height=820')"


class InfoBar:
    """The bar at the bottom of every page (his round 81, instead of the pop-ups): the newest message in one line,
    its colour by kind, and on the right the Debug button with how many lines came since the panel was last
    open. The button opens the Debug panel on the right (DebugList); its pop-out button opens the list in a
    window of its own (/debug)."""

    def __init__(self, log: MessageLog) -> None:
        self._log = log
        self._seen = log.version
        self._icon: ui.icon | None = None
        self._text: ui.label | None = None
        self._count: ui.badge | None = None
        self._drawer: ui.right_drawer | None = None

    def build(self) -> None:
        self._drawer = ui.right_drawer(value=False, bordered=True).props("width=380 overlay") \
            .classes("p-2 gap-2 tb-debug")
        with self._drawer:
            with ui.row().classes("w-full items-center no-wrap gap-1"):
                ui.label("Debug").classes("font-semibold flex-1")
                ui.button(icon="open_in_new", on_click=self._pop_out).props("flat round dense") \
                    .tooltip("Open it in a window of its own")
                ui.button(icon="close", on_click=self._toggle).props("flat round dense")
            DebugList(self._log).build()
        with ui.footer().classes("tb-info-bar px-3 py-0"):
            with ui.row().classes("w-full items-center no-wrap gap-2 min-h-[30px]"):
                self._icon = ui.icon("info").classes("text-sm opacity-0")
                self._text = ui.label("").classes("text-xs flex-1 min-w-0 truncate cursor-pointer")
                self._text.on("click", self._toggle)
                with ui.button(icon="bug_report", on_click=self._toggle).props("flat dense no-caps size=sm") \
                        .tooltip("Debug: every message, flow run and box error"):
                    self._count = ui.badge("").props("color=primary floating rounded")
        last = self._log.entries()[:1]
        if last:
            self.show(last[0], fresh=False)
        self._paint_count()
        ui.timer(1.0, self._paint_count)

    def show(self, entry: MessageEntry, fresh: bool = True) -> None:
        """The newest message in the bar (fresh: it just came, so it lights up for a moment)."""
        if self._text is None:
            return
        icon, colour = look_of(entry)
        self._icon.set_name(icon)
        self._icon.classes(replace=f"text-sm shrink-0 {colour}")
        self._text.set_text(entry.text.replace("\n", " · "))
        self._text._props["title"] = entry.text  # the whole text when the mouse is on it
        self._text.update()
        if fresh:
            self._text.classes(add="tb-info-new")
            ui.timer(1.5, lambda: self._text.classes(remove="tb-info-new"), once=True)

    def _paint_count(self) -> None:
        if self._drawer is not None and self._drawer.value:
            self._seen = self._log.version
        new = max(0, self._log.version - self._seen)
        self._count.set_text(str(new) if new < 100 else "99+")
        self._count.set_visibility(new > 0)

    def _toggle(self) -> None:
        self._drawer.toggle()
        self._seen = self._log.version
        self._paint_count()

    def _pop_out(self) -> None:
        ui.run_javascript(POP_OUT)
        self._drawer.set_value(False)
