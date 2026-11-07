import re
from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.exports.export_finder import ExportFinder
from streamer_toolbox.core.exports.export_importer import ExportImporter
from streamer_toolbox.core.exports.export_part import KINDS, ExportPart
from streamer_toolbox.core.exports.import_row import CHOICES, TAKEN
from streamer_toolbox.core.exports.toolbox_export import ENDING, ToolboxExport

GROUPS = {"alert": "Alerts", "widget": "Widgets", "flow": "Flows", "event": "Events"}
NEVER = "Never inside: tokens, keys, accounts, passwords."
TYPED = "A widget's settings come along as you typed them: an API key in a widget's field too."


class ExportPanel:
    """Settings → Export / Import (his round 86 answer: "an export/import section in the settings ... for now").
    Export: he ticks alerts, widgets, flows or events; the next window lists everything connected to them
    (ExportFinder), each with why it is there, to untick; Export downloads one .toolbox file. Import: he drops a
    .toolbox file; the window lists each part as new, the same as his, or taken (Replace / Keep both / Skip)
    and what the export needs but can't bring; Import brings it in (ExportImporter)."""

    def __init__(self, finder: ExportFinder, importer: ExportImporter) -> None:
        self._finder = finder
        self._importer = importer

    def build(self) -> None:
        picked: set[tuple[str, str]] = set()  # this page's own ticks: every open window has its own
        find = {"text": ""}

        @ui.refreshable
        def choices() -> None:
            with ui.column().classes("w-full gap-1 max-h-[60vh] overflow-auto pr-2"):
                for kind, items in self._finder.choices().items():
                    shown = [(key, title) for key, title in items if find["text"] in title.casefold()]
                    if not shown:
                        continue
                    ticked = sum((kind, key) in picked for key, _ in items)
                    with ui.expansion(f"{GROUPS[kind]} ({len(items)})" + (f", {ticked} ticked" if ticked else ""),
                                      value=bool(find["text"]) or bool(ticked)).props("dense").classes("w-full"):
                        for key, title in shown:
                            ui.checkbox(title, value=(kind, key) in picked,
                                        on_change=lambda e, k=(kind, key): (picked.add if e.value else
                                                                            picked.discard)(k)).props("dense")

        def search(text: str | None) -> None:
            find["text"] = (text or "").casefold()
            choices.refresh()

        def clear() -> None:
            picked.clear()
            choices.refresh()

        with ui.row().classes("w-full gap-4 items-start"):
            with ui.column().classes("flex-1 min-w-[18rem] gap-2"):
                ui.label("Export").classes("text-lg font-semibold")
                ui.label("Tick what you want to give away or keep. What it is connected to (its event, the flow "
                         "that sends it, the flows that flow uses, files) comes along: you see the list before "
                         "saving.").classes("text-sm opacity-80")
                ui.input("Find", on_change=lambda e: search(e.value)).props("dense outlined clearable")                     .classes("w-full")
                choices()
                with ui.row().classes("gap-2"):
                    ui.button("Next: what comes along", icon="arrow_forward",
                              on_click=lambda: self._export(picked)).props("no-caps unelevated")
                    ui.button("Clear", on_click=clear).props("no-caps flat")
            with ui.column().classes("flex-1 min-w-[18rem] gap-2"):
                ui.label("Import").classes("text-lg font-semibold")
                ui.label(f"A {ENDING} file a toolbox exported. Before anything changes, you see what is in it "
                         "and pick what happens to things you have already.").classes("text-sm opacity-80")
                ui.upload(on_upload=lambda e: self._uploaded(e, choices.refresh), auto_upload=True, max_files=1)                     .props(f'accept="{ENDING},.zip" flat bordered label="Press + to pick the file, or drop it here"')                     .classes("w-full")
                ui.label("What someone else made can do everything your own can: look at its flows before you "
                         "switch on what you don't know.").classes("text-xs opacity-60")

    # ---- export ----

    async def _export(self, chosen_here: set[tuple[str, str]]) -> None:
        if not chosen_here:
            ui.notify("Tick at least one thing first.", type="warning")
            return
        picked = sorted(chosen_here, key=lambda k: list(KINDS).index(k[0]))
        ticked: set[tuple[str, str]] = set()
        unticked: set[tuple[str, str]] = set()
        first = self._finder.connected(picked[:1])[0]
        chosen: list[ExportPart] = []  # the list as the window shows it now
        with ui.dialog() as dialog, ui.card().classes("w-[40rem] max-w-full gap-2"):
            ui.label("Export").classes("text-lg font-semibold")
            name = ui.input("Its name", value=first.title if len(picked) == 1 else "My toolbox things") \
                .props("dense outlined").classes("w-full")

            @ui.refreshable
            def parts() -> None:
                found = self._finder.connected(picked, ticked, unticked)
                with ui.column().classes("w-full gap-0 max-h-[50vh] overflow-auto"):
                    for part in found:
                        files = self._finder.files_of(part) if part.ticked else {}
                        with ui.row().classes("w-full items-center no-wrap gap-2"):
                            ui.checkbox(value=part.ticked, on_change=lambda e, p=part: tick(p, e.value)) \
                                .props("dense")
                            with ui.column().classes("gap-0 flex-1 min-w-0"):
                                ui.label(part.label).classes("text-sm" + ("" if part.ticked else " opacity-60"))
                                why = part.why + (f" · {len(files)} file{'s' * (len(files) != 1)}" if files else "")
                                ui.label(why).classes("text-xs opacity-60")
                sizes = [path.stat().st_size for p in found if p.ticked for path in self._finder.files_of(p).values()]
                ui.label(f"{sum(p.ticked for p in found)} things, files inside: {len(sizes)} ({_size(sum(sizes))})") \
                    .classes("text-sm font-medium")
                chosen[:] = found

            def tick(part: ExportPart, on: bool) -> None:
                (ticked.add if on else ticked.discard)(part.id)
                (unticked.discard if on else unticked.add)(part.id)
                parts.refresh()

            parts()
            ui.label(NEVER).classes("text-xs opacity-70")
            ui.label(TYPED).classes("text-xs opacity-60")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("no-caps flat")
                ui.button("Export", icon="file_upload", on_click=lambda: dialog.submit(name.value)) \
                    .props("no-caps unelevated")
        title = await dialog
        _gone(dialog)
        if title is None:
            return
        title = title.strip() or first.title
        export = self._finder.export(title, chosen)
        file = (re.sub(r"[^A-Za-z0-9_.-]+", "_", title).strip("._") or "export") + ENDING
        ui.download.content(export.to_bytes(), file, "application/zip")
        ui.notify(f"{file}: {len(export.entries)} things, {len(export.files)} files", type="positive")

    # ---- import ----

    async def _uploaded(self, e, changed: Callable[[], None]) -> None:
        try:
            export = ToolboxExport.from_bytes(await e.file.read())
            rows = self._importer.rows(export)
            needs = self._importer.needs(export)
        except ValueError as error:
            ui.notify(f"Not imported: {error}", type="negative", multi_line=True)
            return
        finally:
            e.sender.reset()
        picked = {row.id: row.choice for row in rows if row.state == TAKEN}
        with ui.dialog() as dialog, ui.card().classes("w-[40rem] max-w-full gap-2"):
            ui.label(f'Import "{export.title}"').classes("text-lg font-semibold")
            ui.label(f"Made with toolbox {export.app_version}. {len(rows)} things, "
                     f"{len(export.files)} files ({_size(export.size())}).").classes("text-sm opacity-80")
            with ui.column().classes("w-full gap-1 max-h-[50vh] overflow-auto"):
                for row in rows:
                    with ui.row().classes("w-full items-center no-wrap gap-2"):
                        with ui.column().classes("gap-0 flex-1 min-w-0"):
                            ui.label(row.label).classes("text-sm")
                            ui.label(row.said).classes("text-xs " + ("text-warning" if row.state == TAKEN
                                                                     else "opacity-60"))
                        if row.state == TAKEN:
                            ui.select({c: CHOICES[c] for c in row.choices}, value=row.choice,
                                      on_change=lambda ev, r=row: picked.__setitem__(r.id, ev.value)) \
                                .props("dense outlined").classes("w-52")
            if needs:
                ui.label("Needs, not inside:").classes("text-sm font-medium")
                for line in needs:
                    ui.label(f"• {line}").classes("text-xs")
            ui.label("Keep both: the copy gets a new name; a flow comes without its triggers and an alert "
                     "switched off, so nothing plays twice.").classes("text-xs opacity-60")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("no-caps flat")
                ui.button("Import", icon="file_download", on_click=lambda: dialog.submit(True)) \
                    .props("no-caps unelevated")
        go = await dialog
        _gone(dialog)
        if not go:
            return
        try:
            said = self._importer.run(export, picked)
        except (ValueError, OSError) as error:
            ui.notify(f"Import stopped: {error}", type="negative", multi_line=True)
            return
        with ui.dialog() as done, ui.card().classes("w-[32rem] max-w-full gap-1"):
            ui.label(f'"{export.title}" imported').classes("text-lg font-semibold")
            for line in said:
                ui.label(line).classes("text-sm")
            with ui.row().classes("w-full justify-end"):
                ui.button("OK", on_click=done.close).props("no-caps unelevated")
        done.open()
        changed()


def _size(count: int) -> str:
    return f"{count / 1024 ** 2:.1f} MB" if count >= 1024 ** 2 else f"{count / 1024:.0f} KB" if count else "0 KB"


def _gone(dialog: ui.dialog) -> None:
    """Removes a closed window; one whose page went away (a reload while it was open) is gone already."""
    if not dialog.is_deleted:
        try:
            dialog.delete()
        except ValueError:
            pass
