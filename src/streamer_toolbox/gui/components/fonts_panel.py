from nicegui import run, ui

from streamer_toolbox.core.fonts.font_face import FontFace
from streamer_toolbox.core.fonts.font_library import FORMATS, FontLibrary
from streamer_toolbox.core.fonts.installed_fonts import InstalledFonts
from streamer_toolbox.core.fonts.kept_font import KeptFont
from streamer_toolbox.gui.components.font_picker import ALL_DEVICES, THIS_MACHINE

# his 11-18: the warnings come once, when a font is added
OWN_FONT = ("Make sure you may use this font: its license has to allow using it on stream and sharing it with "
            "your other devices. Free fonts (Google Fonts, SIL Open Font License) usually do; some \"free\" fonts "
            "are for personal use only.")
THIS_PC = ("Fine for streaming: OBS and the toolbox on this PC use it by its name. It stays on this machine: a "
           "phone, tablet or another PC shows its own font instead.")
WINDOWS_FONT = " It came with Windows, and Microsoft doesn't allow sharing (hosting) its fonts."
PREVIEW = "The quick brown fox jumps over the lazy dog 0123"


class FontsPanel:
    """Settings → Fonts (his 11-18): the fonts every text can use, each marked 🌐 all devices (the toolbox hosts
    the file) or 🖥 on this machine only (a font of this PC, by name), shown in its own font. Add font: upload a
    file, or take one from this PC (by name; one he installed himself may also be copied in). Files put in the
    fonts folder by hand show up too."""

    def __init__(self, library: FontLibrary, installed: InstalledFonts | None = None) -> None:
        self._library = library
        self._installed = installed or InstalledFonts()

    def build(self) -> None:
        ui.label("Fonts").classes("text-lg font-semibold")
        ui.label(f"Every text can use these. {ALL_DEVICES} All devices: the toolbox hosts the file, so a phone, "
                 f"tablet or OBS on another PC gets it too. {THIS_MACHINE} On this machine only: a font of this PC, "
                 "used by its name.").classes("text-sm opacity-80")
        ui.label(f"Font files put in {self._library.folder} show up here as well.") \
            .classes("text-xs opacity-60 break-all")
        ui.button("Add font", icon="add", on_click=self._add).props("unelevated no-caps")
        self._list()

    @ui.refreshable_method
    def _list(self) -> None:
        fonts = self._library.fonts()
        if not fonts:
            ui.label("No fonts yet.").classes("text-sm opacity-60")
        for font in fonts:
            with ui.row().classes("w-full items-center no-wrap gap-3 py-1 tb-font-row"):
                ui.icon(font.icon).classes("opacity-80").tooltip(font.mark)
                with ui.column().classes("flex-1 min-w-0 gap-0"):
                    ui.label(font.family).classes("text-lg truncate").style(f"font-family: '{_css(font.family)}'")
                    ui.label(font.mark).classes("text-xs opacity-60")
                    for name in font.files:  # his 11-18: one file per line
                        ui.label(name).classes("text-xs opacity-60 truncate")
                ui.button(icon="delete", on_click=lambda f=font: self._remove(f)) \
                    .props("flat round dense color=negative").tooltip("Take it out of the toolbox")

    async def _remove(self, font: KeptFont) -> None:
        what = (f"Delete {', '.join(font.files)} from the fonts folder?" if font.files else
                f"Take {font.family} out of the list? (It stays installed on this PC.)")
        with ui.dialog() as dialog, ui.card():
            ui.label(what)
            ui.label("Texts that use it show another font then.").classes("text-xs opacity-70")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Delete" if font.files else "Take out", on_click=lambda: dialog.submit(True)) \
                    .props("unelevated no-caps color=negative")
        if await dialog:
            self._library.remove(font.family)
            self._list.refresh()
        dialog.delete()

    async def _add(self) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-[620px] max-w-[96vw] gap-3"):
            ui.label("Add font").classes("text-lg font-semibold")
            with ui.tabs().classes("w-full").props("dense no-caps align=left") as tabs:
                upload_tab = ui.tab("Upload a file", icon="upload_file")
                pc_tab = ui.tab("From this PC", icon="computer")
            with ui.tab_panels(tabs, value=upload_tab).classes("w-full"):
                with ui.tab_panel(upload_tab).classes("p-0 gap-2"):
                    self._upload_part()
                with ui.tab_panel(pc_tab).classes("p-0 gap-2"):
                    await self._pc_part()
            with ui.row().classes("w-full justify-end"):
                ui.button("Close", on_click=dialog.close).props("flat no-caps")
        dialog.open()
        await dialog
        dialog.delete()

    def _upload_part(self) -> None:
        _warning(OWN_FONT)
        ui.label(f"{ALL_DEVICES} All devices: the toolbox keeps the file and hosts it.").classes("text-sm")

        async def uploaded(e) -> None:
            try:
                family = self._library.add_file(e.file.name, await e.file.read())
            except Exception as error:
                ui.notify(f"Not added: {error}", type="negative", multi_line=True)
                return
            ui.notify(f"Added {family} (all devices)", type="positive")
            self._list.refresh()

        ui.upload(on_upload=uploaded, auto_upload=True, multiple=True) \
            .props(f'accept="{",".join(FORMATS)}" flat bordered dense '
                   'label="Press + to pick font files (.ttf .otf .woff .woff2), or drop them here"').classes("w-full")

    async def _pc_part(self) -> None:
        loading = ui.label("Reading this PC's fonts ...").classes("text-sm opacity-70")
        families = self._library.not_added(await run.io_bound(self._installed.families))
        loading.delete()
        state: dict[str, list[FontFace]] = {"faces": []}
        picker = ui.select(list(families), label=f"A font of this PC ({len(families)})", with_input=True,
                           on_change=lambda e: show(families.get(e.value or "", []))) \
            .props("outlined dense clearable").classes("w-full")
        details = ui.column().classes("w-full gap-2")

        def show(faces: list[FontFace]) -> None:
            state["faces"] = faces
            details.clear()
            if not faces:
                return
            face = faces[0]
            windows = InstalledFonts.comes_with_windows(face)
            copyable = any(InstalledFonts.copyable(f) for f in faces)
            with details:
                ui.label(PREVIEW).classes("text-xl").style(f"font-family: '{_css(face.family)}'")
                if face.license or face.copyright:
                    ui.label(face.license or face.copyright).classes("text-xs opacity-70")
                if face.license_url:
                    ui.link(face.license_url, face.license_url, new_tab=True).classes("text-xs")
                _warning(THIS_PC + (WINDOWS_FONT if windows else ""))
                ui.button(f"{THIS_MACHINE} Add by name (on this machine only)", on_click=lambda: by_name()) \
                    .props("unelevated no-caps")
                if copyable:
                    ui.separator()
                    ui.label("You installed this one yourself: the toolbox may also keep a copy for all devices.") \
                        .classes("text-sm")
                    _warning(OWN_FONT)
                    ui.button(f"{ALL_DEVICES} Copy into the toolbox (all devices)", on_click=lambda: copy()) \
                        .props("outline no-caps")
                elif not windows:
                    ui.label("Its file can't be hosted (it forbids embedding, or it is a .ttc collection): "
                             "on this machine only.").classes("text-xs opacity-70")

        def by_name() -> None:
            family = state["faces"][0].family
            self._library.add_by_name(family)
            ui.notify(f"Added {family} (on this machine only)", type="positive")
            added()

        def added() -> None:
            """The added font leaves the pick list (his 11-18)."""
            families.pop(state["faces"][0].family, None)
            picker.set_value(None)
            picker.set_options(list(families))
            picker.props(f'label="A font of this PC ({len(families)})"')
            self._list.refresh()

        def copy() -> None:
            try:
                family = self._library.copy_installed(state["faces"])
            except Exception as error:
                ui.notify(f"Not copied: {error}", type="negative", multi_line=True)
                return
            ui.notify(f"Copied {family} into the toolbox (all devices)", type="positive")
            added()


def _warning(text: str) -> None:
    with ui.row().classes("w-full items-start no-wrap gap-2 rounded p-2 bg-amber-500/15"):
        ui.icon("warning", color="warning").classes("mt-0.5")
        ui.label(text).classes("text-sm")


def _css(family: str) -> str:
    return family.replace("\\", "").replace("'", "")
