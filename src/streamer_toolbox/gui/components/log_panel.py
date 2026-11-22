from nicegui import run, ui

from streamer_toolbox.core.system.log_file import LogFile

SHOWN = 300


class LogPanel:
    """Settings → Log (his 11-20): the newest entries of the toolbox's log file, all or only the warnings and
    errors, to read or copy (to send when something odd happened on stream). Read when opened or refreshed,
    never on a timer."""

    def __init__(self, log_file: LogFile) -> None:
        self._file = log_file
        self._least = "DEBUG"

    def build(self) -> None:
        ui.label("Log").classes("text-lg font-semibold")
        ui.label("What the toolbox said lately: connections, errors, requests it couldn't answer. Newest at the "
                 "bottom.").classes("text-sm opacity-80")
        ui.label(f"{self._file.path} (and the older toolbox.log.1 to .3 next to it)") \
            .classes("text-xs opacity-60 break-all")
        with ui.row().classes("items-center gap-2"):
            ui.toggle({"DEBUG": "Everything", "WARNING": "Warnings and errors"}, value=self._least,
                      on_change=lambda e: self._show(e.value)).props("no-caps unelevated dense")
            ui.button("Refresh", icon="refresh", on_click=lambda: self._show(self._least)) \
                .props("flat no-caps dense")
            ui.button("Copy", icon="content_copy", on_click=self._copy).props("flat no-caps dense")
        self._box = ui.scroll_area().classes("w-full h-[60vh] rounded border border-gray-500/30")
        self._show(self._least)

    def _show(self, least: str) -> None:
        self._least = least
        entries = self._file.entries(SHOWN, least)
        self._box.clear()
        with self._box:
            if not entries:
                ui.label("Nothing yet." if least == "DEBUG" else "No warnings or errors.") \
                    .classes("text-sm opacity-60 p-2")
            for entry in entries:
                look = "text-negative" if " ERROR " in entry[:40] or " CRITICAL " in entry[:40] else \
                    "text-warning" if " WARNING " in entry[:40] else ""
                ui.label(entry).classes(f"font-mono text-xs whitespace-pre-wrap break-all px-2 {look}")
        self._box.scroll_to(percent=1.0)

    async def _copy(self) -> None:
        entries = await run.io_bound(self._file.entries, SHOWN, self._least)
        ui.clipboard.write("\n".join(entries))
        ui.notify(f"Copied the last {len(entries)} entries", type="positive")
