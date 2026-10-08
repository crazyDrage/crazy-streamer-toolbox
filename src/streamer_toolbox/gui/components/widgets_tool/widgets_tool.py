from nicegui import ui

from streamer_toolbox.core.widgets.streamelements_elements import StreamElementsElements
from streamer_toolbox.core.widgets.streamelements_fallback import StreamElementsFallback
from streamer_toolbox.core.widgets.streamelements_import import StreamElementsImport
from streamer_toolbox.core.widgets.streamelements_media import StreamElementsMedia
from streamer_toolbox.core.widgets.streamelements_session import StreamElementsSession
from streamer_toolbox.core.widgets.widget_helpers import WidgetHelpers
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore
from streamer_toolbox.gui.components.overlay_source import OverlaySource
from streamer_toolbox.gui.components.widgets_tool.copy_files_question import CopyFilesQuestion
from streamer_toolbox.gui.components.widgets_tool.widget_dialog import WidgetDialog


class WidgetsTool:
    """The Widgets part of the Overlay page: custom widgets in StreamElements' format (the HTML / CSS / JS / FIELDS
    people share), each with its own overlay address for a Browser source. A row per widget: whether OBS shows it,
    its address, Open (preview, settings, code), Add it to OBS, Delete."""

    def __init__(self, store: WidgetStore, hub: WidgetHub, source: OverlaySource, port: int,
                 importer: StreamElementsImport | None = None,
                 fallback: StreamElementsFallback | None = None,
                 elements: StreamElementsElements | None = None,
                 latest: StreamElementsSession | None = None) -> None:
        self._latest = latest
        self._importer = importer
        self._elements = elements
        self._fallback = fallback
        self._store = store
        self._hub = hub
        self._source = source
        self._port = port
        self._media = StreamElementsMedia(store)
        self._helpers = WidgetHelpers(store)

    def build(self) -> None:
        with ui.card().classes("w-full gap-1"):
            ui.label("Custom widgets").classes("text-lg font-semibold")
            ui.label("Widget code made for StreamElements (HTML, CSS, JS, FIELDS) runs here: paste the four parts, "
                     "and the toolbox gives the code what StreamElements would: follows, subs, gifts, cheers, "
                     "raids, chat messages, the settings, and a place to keep its data. Each widget is its own "
                     "Browser source.").classes("text-sm opacity-80")
            ui.label("Not there: StreamElements' own services (tips, their store and merch, their bot's counters, "
                     "their web API with your channel's key). A widget that needs those shows up but stays empty "
                     "there.").classes("text-xs opacity-60")
            if self._fallback is not None:
                ui.switch("Ask StreamElements when the toolbox can't answer", value=self._fallback.on,
                          on_change=lambda e: self._fallback.set(e.value)).props("dense") \
                    .tooltip("Off: widgets never reach StreamElements' web API. Who a channel is (picture, Twitch "
                             "id) comes from your Twitch login; other questions stay unanswered. On: the toolbox "
                             "asks StreamElements for those and hands the answer to the widget")
        # windows are made in here, not in a row: the rows are drawn again every few seconds, and a window made
        # inside one would go with it. One per open page (this tool is shared by every page that shows it)
        windows = ui.element("div")
        self._rows(windows)
        ui.timer(3.0, self._rows.refresh)  # "OBS shows it" changes without a click here
        with ui.row().classes("gap-2"):
            ui.button("New widget", icon="add", on_click=lambda: self._open(windows, None)).props("no-caps outline")
            if self._importer is not None:
                ui.button("Import from StreamElements", icon="cloud_download",
                          on_click=lambda: self._import(windows)).props("no-caps outline") \
                    .tooltip("Takes the custom widgets out of one of your StreamElements overlays, or brings "
                             "one of your Elements over")
            if self._latest is not None:
                ui.button("Latest names from StreamElements", icon="history", on_click=self._bring_latest) \
                    .props("no-caps outline") \
                    .tooltip("The toolbox only knows the subs, cheers, raids and tips it saw itself, so a \"latest "
                             "subscriber\" label is empty until the next one. This asks StreamElements once for "
                             "the ones it knows and keeps them. What the toolbox saw itself stays")
            ui.button("Add the example", icon="school", on_click=self._add_example).props("no-caps flat") \
                .tooltip("A small widget to try and to read: latest follower and chat lines")

    def _address(self, name: str) -> str:
        return f"http://127.0.0.1:{self._port}/overlay/widget/{name}"

    @ui.refreshable_method
    def _rows(self, windows: ui.element) -> None:
        names = self._store.names()
        if not names:
            ui.label("No widgets yet.").classes("opacity-70")
        for name in names:
            address = self._address(name)
            shown = self._hub.pages(name)
            with ui.card().classes("w-full"), ui.row().classes("items-center no-wrap w-full gap-2"):
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label(name).classes("text-lg font-semibold")
                    with ui.row().classes("items-center gap-1"):
                        ui.label(address).classes("font-mono text-xs break-all")
                        ui.button(icon="content_copy", on_click=lambda a=address: (
                            ui.clipboard.write(a), ui.notify("Address copied"))).props("flat round dense size=sm")
                    ui.label(f"{shown} Browser source{'s show' if shown > 1 else ' shows'} it." if shown
                             else "OBS isn't showing it yet.") \
                        .classes("text-xs " + ("text-positive" if shown else "text-warning"))
                ui.button("Open", icon="tune", on_click=lambda n=name: self._open(windows, n)) \
                    .props("no-caps unelevated") \
                    .tooltip("Preview, settings, test events and its code")
                ui.button("Add it to OBS", icon="add_to_queue", on_click=lambda n=name: self._add_to_obs(windows, n)) \
                    .props("no-caps outline")
                ui.button(icon="delete", on_click=lambda n=name: self._delete(windows, n)).props("flat round dense") \
                    .tooltip("Delete this widget")

    async def _import(self, windows: ui.element) -> None:
        try:
            mine = await self._importer.overlays()
            if self._elements is not None:
                found = await self._elements.elements()
                mine = {**mine, **{key: f"Element: {title}" for key, title in found.items()}}
            problem = ""
        except Exception as e:  # no token, StreamElements not reachable: pasting an address may still say why
            mine, problem = {}, str(e).strip("'\"") or type(e).__name__
        with windows, ui.dialog() as dialog, ui.card().classes("w-[36rem] max-w-full gap-3"):
            ui.label("Import from StreamElements").classes("text-lg font-semibold")
            ui.label("Pick one of your overlays. Every custom widget in it comes over with its code and the "
                     "settings you made there, and the files it uses are copied to this PC. Their built-in "
                     "widgets (alert box, labels) have no code to take. "
                     "Needs the StreamElements token (Connections → StreamElements); it only reads.") \
                .classes("text-sm opacity-80")
            ui.label("Or pick one of your Elements (scene packages, tickers: the Elements tab on "
                     "StreamElements). It comes over as it is published there, and its pictures, videos, sounds "
                     "and fonts are copied to this PC, so that can take a moment.").classes("text-sm opacity-80")
            if problem:
                ui.label(f"Your overlays can't be listed: {problem}").classes("text-sm text-warning")
            picked = ui.select(mine, label=f"Your overlays and Elements ({len(mine)})", with_input=True) \
                .props("outlined dense options-dense").classes("w-full")
            address = ui.input(placeholder="or paste its address from StreamElements' editor") \
                .props("outlined dense").classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Import", icon="cloud_download",
                          on_click=lambda: dialog.submit((address.value or "").strip() or picked.value)) \
                    .props("unelevated no-caps")
        pasted = await dialog
        dialog.delete()
        if not pasted:
            return
        with windows:
            if not await CopyFilesQuestion("Import it with its files?").ask():
                return
        if self._elements is not None and self._elements.instance_id(pasted):
            await self._import_element(pasted)
            return
        try:
            overlay = await self._importer.fetch(pasted)
            widgets = self._importer.widgets(overlay, self._store.names())
        except Exception as e:
            ui.notify(str(e).strip("'\"") or type(e).__name__, type="negative", multi_line=True)
            return
        waiting = ui.notification("Copying the widgets' files to this PC…", spinner=True, timeout=None)
        missed: list[str] = []
        try:
            for widget in widgets:
                self._store.save(widget)
                missed += (await self._media.keep(widget.name))[1] + (await self._helpers.keep(widget.name))[1]
        finally:
            waiting.dismiss()
        self._rows.refresh()
        if widgets and missed:
            ui.notify("Imported: " + ", ".join(w.name for w in widgets) + f", but {len(missed)} of their files "
                      "couldn't be fetched (the widget's Safety tab can try again): " + ", ".join(missed[:3]),
                      type="warning", multi_line=True)
        elif widgets:
            ui.notify("Imported: " + ", ".join(w.name for w in widgets) + ". Everything they need is on this "
                      "PC. Open shows it.", type="positive", multi_line=True)
        else:
            kinds = sorted({str(w.get("type")) for w in overlay.get("widgets", [])}) or ["nothing"]
            ui.notify(f"No custom widget in that overlay (it has: {', '.join(kinds)}).", type="warning",
                      multi_line=True)

    async def _import_element(self, pasted: str) -> None:
        waiting = ui.notification("Fetching the Element and its files…", spinner=True, timeout=None)
        try:
            widget, missed = await self._elements.bring(pasted, self._store)
        except Exception as e:
            ui.notify(str(e).strip("'\"") or type(e).__name__, type="negative", multi_line=True)
            return
        finally:
            waiting.dismiss()
        self._rows.refresh()
        if missed:
            ui.notify(f"Imported as {widget.name}, but {len(missed)} of its files couldn't be fetched, so those "
                      "parts stay empty: " + ", ".join(missed[:3]), type="warning", multi_line=True)
        else:
            ui.notify(f"Imported as {widget.name}. Open shows it.", type="positive")

    async def _bring_latest(self) -> None:
        try:
            filled = await self._latest.bring(self._hub.session)
        except Exception as e:
            ui.notify(str(e).strip("'\"") or type(e).__name__, type="negative", multi_line=True)
            return
        if not filled:
            ui.notify("Nothing to bring: the toolbox already has a latest one for everything StreamElements "
                      "knows.", type="info", multi_line=True)
            return
        for name in self._store.names():
            self._hub.reload(name)  # the open widget pages read the names when they load
        ui.notify("Brought from StreamElements, the latest: " + ", ".join(filled), type="positive", multi_line=True)

    def _add_example(self) -> None:
        name = self._store.add_example()
        self._rows.refresh()
        ui.notify(f"{name} is in the list: Open shows it", type="positive")

    def _open(self, windows: ui.element, name: str | None) -> None:
        """The widget's window; None = a new one."""
        widget = self._store.get(name) if name else None
        if name and widget is None:
            ui.notify(f"The widget {name} is gone", type="warning")
            self._rows.refresh()
            return
        with windows:
            WidgetDialog(self._store, self._hub, widget, self._rows.refresh).open()

    async def _add_to_obs(self, windows: ui.element, name: str) -> None:
        with windows:
            await self._source.ask_and_add(f"toolbox widget {name}", self._address(name))

    async def _delete(self, windows: ui.element, name: str) -> None:
        with windows, ui.dialog() as dialog, ui.card().classes("w-96 gap-3"):
            ui.label(f"Delete the widget {name}?").classes("text-lg font-semibold")
            ui.label("Its code, its settings and what it kept are removed from this PC (config/widgets). A Browser "
                     "source in OBS that shows it stays, showing nothing.").classes("text-sm opacity-80")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Delete", on_click=lambda: dialog.submit(True)).props("unelevated no-caps color=negative")
        sure = await dialog
        dialog.delete()
        if sure:
            self._store.delete(name)
            self._rows.refresh()
            ui.notify(f"Widget {name} deleted")
