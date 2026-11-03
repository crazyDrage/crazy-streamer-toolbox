from nicegui import ui

from streamer_toolbox.core.interfaces.import_target import ImportTarget
from streamer_toolbox.core.interfaces.importer import Importer
from streamer_toolbox.core.widgets.streamelements_cleaner import StreamElementsCleaner
from streamer_toolbox.core.widgets.streamelements_elements import StreamElementsElements
from streamer_toolbox.core.widgets.streamelements_import import StreamElementsImport
from streamer_toolbox.core.widgets.streamelements_session import StreamElementsSession
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore
from streamer_toolbox.gui.components.widgets_tool.copy_files_question import CopyFilesQuestion


class StreamElementsImporter(Importer):
    """The toolbox's own importer for StreamElements (his round 64: the import apart from the widgets, the
    result handed to Widgets): the custom widgets of one of his overlays, or one of his Elements, and once the
    latest names StreamElements knows. "Clean out StreamElements" is on at the start (his answer 2.3): the
    imported widgets get their StreamElements links and files written into them (StreamElementsCleaner). The
    same for a widget he already has is here too, not in the widget window (his round 72)."""

    title = "StreamElements"
    icon = "cloud_download"
    description = "Your custom widgets and Elements, and the latest names it knows. Only reads."

    def __init__(self, source: StreamElementsImport, elements: StreamElementsElements,
                 latest: StreamElementsSession, store: WidgetStore, hub: WidgetHub,
                 cleaner: StreamElementsCleaner) -> None:
        self._source = source
        self._elements = elements
        self._latest = latest
        self._store = store
        self._hub = hub
        self._cleaner = cleaner

    def build(self, target: ImportTarget) -> None:
        # windows and fields are made per page: this importer is shared by every open page
        windows = ui.element("div")
        ui.label("Pick one of your overlays: every custom widget in it comes over with its code and the settings "
                 "you made there (their built-in widgets, alert box and labels, have no code to take). Or pick "
                 "one of your Elements (scene packages, tickers): it comes over as published, with its pictures, "
                 "videos, sounds and fonts. Needs the StreamElements token (Connections → StreamElements).") \
            .classes("text-sm opacity-80")
        picked = ui.select({}, label="Your overlays and Elements (open the list: it asks StreamElements)",
                           with_input=True).props("outlined dense options-dense").classes("w-full")
        # on focus, not popup-show: an empty list never opens, so it never asked StreamElements (his round 84)
        picked.on("focus", lambda: self._list(picked))
        address = ui.input(placeholder="or paste its address from StreamElements' editor") \
            .props("outlined dense").classes("w-full")
        clean = ui.switch("Clean out StreamElements", value=True).props("dense") \
            .tooltip("Writes into the widgets: their streamelements.com links point at the toolbox, and the files "
                     "they load from StreamElements and other servers are copied to this PC. Then they need "
                     "neither StreamElements nor the internet")
        with ui.row().classes("gap-2"):
            ui.button("Import", icon="cloud_download",
                      on_click=lambda: self._import(target, windows, (address.value or "").strip() or picked.value,
                                                    clean.value)).props("unelevated no-caps")
            ui.button("Latest names", icon="history", on_click=self._bring_latest).props("no-caps outline") \
                .tooltip("The toolbox only knows the subs, cheers, raids and tips it saw itself, so a \"latest "
                         "subscriber\" label is empty until the next one. This asks StreamElements once for the "
                         "ones it knows and keeps them. What the toolbox saw itself stays")
        # his round 72: not in the widget window, which knows nothing about StreamElements
        ui.label("A widget you already have").classes("text-sm font-semibold pt-2")
        with ui.row().classes("items-center gap-2 w-full"):
            had = ui.select(self._store.names(), label="Widget", with_input=True) \
                .props("outlined dense options-dense").classes("flex-1 min-w-[12rem]")
            had.on("popup-show", lambda: had.set_options(self._store.names(), value=had.value))
            ui.button("Clean out StreamElements", icon="cleaning_services",
                      on_click=lambda: self._clean(windows, had.value)).props("no-caps outline") \
                .tooltip("Writes into the widget: every streamelements.com address points at the toolbox, and the "
                         "files it loads from StreamElements and other servers are copied to this PC. Then it "
                         "needs neither StreamElements nor the internet")

    async def _clean(self, windows: ui.element, name: str | None) -> None:
        if not name or self._store.get(name) is None:
            ui.notify("Pick one of your widgets", type="warning")
            return
        with windows:
            if not await CopyFilesQuestion("Copy this widget's files to this PC?", "I may use them: copy").ask():
                return
        waiting = ui.notification("Copying the widget's files to this PC…", spinner=True, timeout=None)
        try:
            changed, missed = await self._cleaner.clean(name)
        except Exception as e:
            ui.notify(str(e).strip("'\"") or type(e).__name__, type="negative", multi_line=True)
            return
        finally:
            waiting.dismiss()
        self._hub.reload(name)
        links = f"{name}: {changed} StreamElements link{'s' if changed != 1 else ''} point at the toolbox now"
        if missed:
            ui.notify(f"{links}, but {len(missed)} files couldn't be fetched: " + ", ".join(missed[:3]),
                      type="warning", multi_line=True)
        else:
            ui.notify(f"{links}. Everything it needs is on this PC.", type="positive")

    async def _list(self, picked: ui.select) -> None:
        """Lists his overlays and Elements the first time the list opens (it asks StreamElements)."""
        if picked.options or getattr(picked, "tb_listing", False):
            return
        picked.tb_listing = True  # one ask at a time (focus comes again while it waits)
        waiting = ui.notification("Asking StreamElements for your overlays and Elements…", spinner=True,
                                  timeout=None)
        try:
            mine = await self._source.overlays()
            found = await self._elements.elements()
        except Exception as e:  # no token, StreamElements not reachable: pasting an address may still work
            ui.notify(f"Your overlays can't be listed: {str(e).strip(chr(39) + chr(34)) or type(e).__name__}",
                      type="warning", multi_line=True)
            return
        finally:
            waiting.dismiss()
            picked.tb_listing = False
        options = {**mine, **{key: f"Element: {title}" for key, title in found.items()}}
        if not options:
            ui.notify("StreamElements has no overlays or Elements on your account", type="info")
            return
        picked.set_options(options)
        picked.run_method("showPopup")

    async def _import(self, target: ImportTarget, windows: ui.element, pasted: str | None, clean: bool) -> None:
        if not pasted:
            ui.notify("Pick an overlay or an Element, or paste its address", type="warning")
            return
        element = bool(self._elements.instance_id(pasted))
        if element or clean:  # both copy files to this PC
            with windows:
                if not await CopyFilesQuestion("Import it with its files?").ask():
                    return
        if element:
            await self._import_element(pasted)
            return
        try:
            overlay = await self._source.fetch(pasted)
            widgets = self._source.widgets(overlay, target.widget_names())
        except Exception as e:
            ui.notify(str(e).strip("'\"") or type(e).__name__, type="negative", multi_line=True)
            return
        if not widgets:
            kinds = sorted({str(w.get("type")) for w in overlay.get("widgets", [])}) or ["nothing"]
            ui.notify(f"No custom widget in that overlay (it has: {', '.join(kinds)}).", type="warning",
                      multi_line=True)
            return
        names = [target.add_widget(widget) for widget in widgets]
        missed: list[str] = []
        if clean:
            waiting = ui.notification("Copying the widgets' files to this PC…", spinner=True, timeout=None)
            try:
                for name in names:
                    missed += (await self._cleaner.clean(name))[1]
            finally:
                waiting.dismiss()
        done = "Imported: " + ", ".join(names) + " (Overlay → Widgets)"
        if missed:
            ui.notify(f"{done}, but {len(missed)} of their files couldn't be fetched (the widget's Safety tab can "
                      "try again): " + ", ".join(missed[:3]), type="warning", multi_line=True)
        else:
            ui.notify(done + (". Everything they need is on this PC." if clean else "."), type="positive",
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
        if missed:
            ui.notify(f"Imported as {widget.name}, but {len(missed)} of its files couldn't be fetched, so those "
                      "parts stay empty: " + ", ".join(missed[:3]), type="warning", multi_line=True)
        else:
            ui.notify(f"Imported as {widget.name} (Overlay → Widgets).", type="positive")

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
