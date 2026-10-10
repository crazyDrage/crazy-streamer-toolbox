from pathlib import Path

from nicegui import ui

from streamer_toolbox.core.files.file_browser import FileBrowser
from streamer_toolbox.core.files.file_types import FOLDER


class FileDialog:
    """The file window for a box's file field: the folders of this PC (so it works from the tablet too, and gives
    the real path), the files the field takes (All files shows the rest), places to jump to, and a name to type
    for a file that isn't there yet (a screenshot, a text file to write). FOLDER as endings picks a folder."""

    _last: Path | None = None  # the folder the last pick came from: the next window opens there

    def __init__(self, endings: tuple[str, ...] = (), browser: FileBrowser | None = None) -> None:
        self._endings = tuple(endings)
        self._browser = browser or FileBrowser()
        self._folder = Path.home()
        self._all = False

    async def open(self, value: str = "") -> str | None:
        """Opens the window where the field's value is; the picked path, or None."""
        self._folder = self._browser.start(value, FileDialog._last)
        folders_only = self._endings == FOLDER
        with ui.dialog() as dialog, ui.card().classes("w-[44rem] max-w-full h-[80vh] gap-2 p-3"):
            self._dialog = dialog
            with ui.row().classes("items-center w-full no-wrap gap-2"):
                ui.label("Pick a folder" if folders_only else "Pick a file").classes("text-lg font-semibold flex-1")
                if self._endings and not folders_only:
                    ui.switch("All files", on_change=lambda e: self._show_all(e.value)).props("dense")
                ui.button(icon="close", on_click=lambda: dialog.submit(None)).props("flat round dense")
            with ui.row().classes("items-center w-full no-wrap gap-2"):
                ui.button(icon="arrow_upward", on_click=self._up).props("flat round dense").tooltip("Folder above")
                self._path = ui.input(value=str(self._folder)).props("outlined dense").classes("flex-1 min-w-0")
                self._path.on("keydown.enter", lambda: self._go(Path(self._path.value.strip())))
                ui.select(self._browser.places(), label="Go to",
                          on_change=lambda e: e.value and self._go(Path(e.value))) \
                    .props("outlined dense options-dense").classes("w-36 shrink-0")
            with ui.element("div").classes("flex-1 min-h-0 w-full overflow-y-auto border border-gray-500/30 rounded"):
                self._list()
            with ui.row().classes("items-center w-full no-wrap gap-2"):
                if folders_only:
                    ui.space()
                    ui.button("Use this folder", on_click=lambda: self._take(self._folder)).props("unelevated no-caps")
                else:
                    name = ui.input(placeholder="or type a file name (for a new file)").props("outlined dense") \
                        .classes("flex-1 min-w-0")
                    name.on("keydown.enter", lambda: self._take_name(name.value))
                    ui.button("Use", on_click=lambda: self._take_name(name.value)).props("unelevated no-caps")
        result = await dialog
        dialog.delete()
        return result

    @ui.refreshable_method
    def _list(self) -> None:
        listing = self._browser.listing(self._folder, () if self._all else self._endings)
        if listing.problem:
            ui.label(f"Can't open {self._folder}: {listing.problem}").classes("text-warning p-2")
            return
        for name in listing.folders:
            self._row("folder", name, lambda n=name: self._go(self._folder / n))
        for name in listing.files:
            self._row("description", name, lambda n=name: self._take(self._folder / n))
        if not listing.folders and not listing.files:
            what = "No folders in here." if self._endings == FOLDER else "Nothing in here that fits." \
                if self._endings and not self._all else "This folder is empty."
            ui.label(what).classes("opacity-70 p-2")

    @staticmethod
    def _row(icon: str, name: str, on_click) -> None:
        with ui.row().classes("items-center no-wrap gap-2 w-full px-2 py-1 cursor-pointer hover:bg-gray-500/15") \
                .on("click", on_click):
            ui.icon(icon).classes("opacity-70" + (" text-primary" if icon == "folder" else ""))
            ui.label(name).classes("break-all")

    def _go(self, folder: Path) -> None:
        if folder.is_file():  # a whole path typed or pasted
            self._take(folder)
            return
        self._folder = folder
        self._path.set_value(str(folder))
        self._list.refresh()

    def _up(self) -> None:
        if self._folder.parent != self._folder:
            self._go(self._folder.parent)

    def _show_all(self, on: bool) -> None:
        self._all = on
        self._list.refresh()

    def _take_name(self, name: str) -> None:
        if (name or "").strip():
            self._take(self._folder / name.strip())

    def _take(self, path: Path) -> None:
        FileDialog._last = path if self._endings == FOLDER else path.parent
        self._dialog.submit(str(path))
