from nicegui import ui

from streamer_toolbox.gui.services.message_entry import MessageEntry
from streamer_toolbox.gui.services.message_log import MessageLog

# kind → (icon, colour class)
LOOKS = {
    "positive": ("check_circle", "text-positive"),
    "negative": ("error", "text-negative"),
    "warning": ("warning", "text-warning"),
    "ongoing": ("hourglass_top", "opacity-70"),
    "run": ("play_arrow", "opacity-60"),
}
INFO = ("info", "opacity-70")


def look_of(entry: MessageEntry) -> tuple[str, str]:
    return LOOKS.get(entry.kind, INFO)


class DebugList:
    """The Debug list (his round 81): every message, flow run and box error, newest on top, with a search and
    Clear. Shown in the panel on the right of every page and on its own page (/debug, the pop-out window); it
    looks for new lines once a second while it is open."""

    def __init__(self, log: MessageLog) -> None:
        self._log = log
        self._search = ""

    def build(self, title: bool = False) -> None:
        """title: the pop-out window's own heading (the panel has its own line with the buttons)."""
        if title:
            ui.label("Debug").classes("font-semibold")
        with ui.row().classes("w-full items-center no-wrap gap-1"):
            ui.input(placeholder="Search", on_change=self._searched).props("dense outlined clearable") \
                .classes("flex-1 min-w-0")
            ui.button(icon="delete_sweep", on_click=self._clear).props("flat round dense") \
                .tooltip("Clear the list")
        self._lines()
        seen = [self._log.version]

        def follow() -> None:
            if self._log.version != seen[0]:
                seen[0] = self._log.version
                self._lines.refresh()

        ui.timer(1.0, follow)

    def _searched(self, e) -> None:
        self._search = (e.value or "").strip().casefold()
        self._lines.refresh()

    def _clear(self) -> None:
        self._log.clear()
        self._lines.refresh()

    @ui.refreshable_method
    def _lines(self) -> None:
        entries = [e for e in self._log.entries() if not self._search or self._search in e.text.casefold()]
        if not entries:
            ui.label("Nothing yet" if not self._search else "Nothing matches").classes("text-xs opacity-60 p-2")
            return
        with ui.column().classes("w-full gap-0"):
            for entry in entries:
                icon, colour = look_of(entry)
                with ui.row().classes("w-full items-start no-wrap gap-2 py-1 border-b border-[var(--tb-line)]"):
                    ui.label(entry.time).classes("text-xs font-mono opacity-60 shrink-0 pt-px")
                    ui.icon(icon).classes(f"text-sm shrink-0 pt-px {colour}")
                    ui.label(entry.text).classes("text-xs break-words whitespace-pre-line min-w-0")
