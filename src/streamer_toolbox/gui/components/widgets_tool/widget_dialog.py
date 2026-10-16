import json
import uuid
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from nicegui import ui

from streamer_toolbox.core.widgets.element_settings import ElementSettings
from streamer_toolbox.core.widgets.streamelements_links import without_streamelements_links
from streamer_toolbox.core.widgets.streamelements_media import StreamElementsMedia
from streamer_toolbox.core.widgets.widget import Widget, check_name
from streamer_toolbox.core.widgets.widget_events import TEST_EVENTS
from streamer_toolbox.core.widgets.widget_helpers import WidgetHelpers
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_safety import ALWAYS, HOST_NAME, MODES, WidgetSafety
from streamer_toolbox.core.widgets.widget_store import WidgetStore, parse_fields
from streamer_toolbox.gui.components.widgets_tool.copy_files_question import CopyFilesQuestion
from streamer_toolbox.gui.components.widgets_tool.widget_fields_form import WidgetFieldsForm

PARTS = (("html", "HTML", "HTML"), ("css", "CSS", "CSS"), ("js", "JS", "JavaScript"), ("fields", "FIELDS", "JSON"))
# a file in a widget's data folder → what it is
DATA_FILES = {"store.json": "what the widget's own code kept (its counters, lists, last state)",
              "channels.json": "channel pictures and ids looked up on Twitch",
              "emotes.json": "emote lists from BetterTTV and FrankerFaceZ"}
CANVAS = (1920, 1080)  # the preview shows the widget as on a canvas of this size, shrunk to fit


class WidgetDialog:
    """One widget's window. A new one: its name and the four parts to paste (HTML, CSS, JS, FIELDS). An existing
    one also has a preview on the left (the real widget page, shrunk from a 1920 × 1080 canvas) with test events
    below it, and a Settings tab drawn from its FIELDS; an imported StreamElements Element has no FIELDS, its
    Settings tab is drawn from its settings file instead (ElementSettings: texts, colours, sizes, volume, how
    long an alert stays, where a piece sits). Saving code or changing a setting makes every page of the widget
    load again (OBS too)."""

    def __init__(self, store: WidgetStore, hub: WidgetHub, widget: Widget | None,
                 on_saved: Callable[[], None]) -> None:
        self._store = store
        self._hub = hub
        self._widget = widget
        self._on_saved = on_saved
        self._code = {"html": widget.html if widget else "", "css": widget.css if widget else "",
                      "js": widget.js if widget else "",
                      "fields": json.dumps(widget.fields, indent=2, ensure_ascii=False) if widget and widget.fields
                      else ""}
        self._editors: dict[str, ui.codemirror] = {}
        self._helpers = WidgetHelpers(store)
        self._media = StreamElementsMedia(store)

    def open(self) -> None:
        widget = self._widget
        with ui.dialog().props("persistent") as dialog, \
                ui.card().classes(("w-[88rem]" if widget else "w-[56rem]") + " max-w-full gap-3"):
            self._dialog = dialog
            self._windows = ui.element("div")  # questions open here: outside the parts that redraw
            with ui.row().classes("items-center no-wrap w-full gap-2"):
                ui.label(f"Widget: {widget.name}" if widget else "New widget").classes("text-lg font-semibold")
                self._name = None if widget else ui.input(placeholder="Name, e.g. chat_box") \
                    .props("outlined dense autofocus").classes("w-64")
                ui.space()
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")
            with ui.element("div").classes("flex flex-col lg:flex-row w-full gap-4"):
                if widget:
                    with ui.column().classes("flex-1 min-w-0 gap-2"):
                        self._preview(widget.name)
                with ui.column().classes("gap-2 min-w-0 " + ("w-full lg:w-[37rem] shrink-0" if widget else "w-full")):
                    self._tabs()
        dialog.open()

    def _preview(self, name: str) -> None:
        box, frame = f"box_{uuid.uuid4().hex[:8]}", f"frame_{uuid.uuid4().hex[:8]}"
        width, height = CANVAS
        with ui.element("div").props(f"id={box}").classes("w-full rounded overflow-hidden border border-gray-500/30") \
                .style(f"aspect-ratio: {width} / {height}; background: repeating-conic-gradient(#2a2a2a 0% 25%, "
                       "#1c1c1c 0% 50%) 0 0 / 24px 24px"):
            ui.element("iframe").props(f"id={frame} src=/overlay/widget/{name}?preview=1 allow=autoplay") \
                .style(f"width: {width}px; height: {height}px; border: 0; display: block; "
                       "transform-origin: top left; color-scheme: light")
        ui.run_javascript(f"""
            (() => {{
                const box = document.getElementById("{box}"), frame = document.getElementById("{frame}");
                if (!box || !frame) return;
                const fit = () => {{ frame.style.transform = "scale(" + box.clientWidth / {width} + ")"; }};
                new ResizeObserver(fit).observe(box);
                fit();
            }})();""")
        with ui.row().classes("items-center gap-2"):
            ui.label("Test:").classes("text-sm opacity-70")
            for listener, (title, _) in TEST_EVENTS.items():
                if listener != "message":
                    ui.button(title, on_click=lambda l=listener: self._hub.test(name, l)) \
                        .props("no-caps outline dense")
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            chat = ui.input(placeholder="Chat text to test, e.g. a command of the widget like !spin") \
                .props("outlined dense").classes("flex-1 min-w-0")
            send = ui.button("Chat message", on_click=lambda: self._hub.test(name, "message", chat.value or "")) \
                .props("no-caps outline dense")
            chat.on("keydown.enter", lambda: send.run_method("click"))
        ui.label("Test events go to this preview and to the widget in OBS. Nothing is saved from them. A chat "
                 "text you type is sent as you (the streamer); empty = a viewer says hello.") \
            .classes("text-xs opacity-60")

    def _tabs(self) -> None:
        widget = self._widget
        with ui.tabs().props("dense inline-label no-caps align=left").classes("w-full") as tabs:
            settings = ui.tab("settings", label="Settings", icon="tune") if widget else None
            for part, title, _ in PARTS:
                ui.tab(part, label=title)
            data = ui.tab("data", label="Data") if widget else None
            safety = ui.tab("safety", label="Safety") if widget else None
        with ui.tab_panels(tabs, value=settings or "html").props("animated=false").classes("w-full bg-transparent"):
            if widget:
                with ui.tab_panel(settings).classes("p-0 pt-2 gap-2"):
                    with ui.column().classes("w-full gap-2 max-h-[60vh] overflow-y-auto pr-1"):
                        element = ElementSettings.of(widget)
                        if element is not None:
                            ui.label("This is an Element from StreamElements. Each piece of it is a section: its "
                                     "text, colours, size, volume, how long it stays and where it sits "
                                     "(in pixels on a 1920 × 1080 canvas).").classes("text-sm opacity-80")
                            WidgetFieldsForm(Widget(widget.name, fields=element.fields()), self._set_element,
                                             lambda field, value: None).build()
                        else:
                            WidgetFieldsForm(widget, self._set_values,
                                             lambda field, value: self._hub.button(widget.name, field, value)).build()
                with ui.tab_panel(data).classes("p-0 pt-2 gap-2"):
                    self._data()
                with ui.tab_panel(safety).classes("p-0 pt-2 gap-2"):
                    with ui.column().classes("w-full gap-2 max-h-[60vh] overflow-y-auto pr-1"):
                        self._safety()
            for part, _, language in PARTS:
                with ui.tab_panel(part).classes("p-0 pt-2"):
                    self._editors[part] = ui.codemirror(
                        self._code[part], language=language, theme="vscodeDark",
                        on_change=lambda e, p=part: self._code.__setitem__(p, e.value)).classes("w-full h-[55vh]")
        with ui.row().classes("w-full items-center justify-end gap-2"):
            ui.label("Code from the internet runs in the overlay page: it can't touch this PC. Where it may "
                     "talk to is on the Safety tab.").classes("text-xs opacity-60 flex-1")
            ui.button("Remove StreamElements links", icon="link_off", on_click=self._remove_links) \
                .props("no-caps outline") \
                .tooltip("Rewrites every streamelements.com address in the HTML, CSS and JS so it points at the "
                         "toolbox's own stand-in (/overlay/streamelements/..., on the page this widget's own). The code then never calls "
                         "StreamElements. The page already does this when it is shown; this changes the code "
                         "itself")
            ui.button("Save code", icon="save", on_click=self._save).props("no-caps unelevated")

    @ui.refreshable_method
    def _data(self) -> None:
        """What the widget gathered while it ran: all of it is in its own data folder and goes in one click."""
        name = self._widget.name
        files = self._store.data_files(name)
        ui.label("Everything this widget gathers while it runs is kept in its own folder, apart from the rest of "
                 "the toolbox:").classes("text-sm opacity-80")
        ui.label(str(self._store.data_folder(name))).classes("font-mono text-xs break-all")
        if not files:
            ui.label("Nothing there yet.").classes("text-sm opacity-70")
        for file, size in files.items():
            with ui.row().classes("items-baseline no-wrap gap-2 w-full"):
                ui.label(file).classes("font-mono text-sm")
                ui.label(f"{max(size // 1024, 1)} KB").classes("text-xs opacity-60")
                ui.label(DATA_FILES.get(file, "")).classes("text-xs opacity-70 flex-1")
        with ui.row().classes("items-center gap-2"):
            ui.button("Remove all of it", icon="delete_sweep", on_click=self._clear_data) \
                .props("no-caps outline color=negative").set_enabled(bool(files))
            ui.button(icon="refresh", on_click=self._data.refresh).props("flat round dense").tooltip("Look again")
        ui.label("The widget's code and your settings stay. Looked-up things are fetched again when the widget "
                 "needs them; what the widget's own code kept is gone for good.").classes("text-xs opacity-60")

    @ui.refreshable_method
    def _safety(self) -> None:
        """The fences around the widget's code (WidgetSafety): away from the toolbox's own pages, and only the
        hosts he allows."""
        widget, name = self._widget, self._widget.name
        safety = self._store.safety(name)
        ui.label("A widget is someone else's program. It can't read files or start anything on this PC. These "
                 "two fences keep it to itself as well.").classes("text-sm opacity-80")
        ui.switch("Keep it away from the toolbox's own pages", value=safety.sandbox,
                  on_change=lambda e: self._set_safety(sandbox=e.value)).props("dense") \
            .tooltip("On: the widget's code can't read the toolbox's pages, settings or other widgets (the same "
                     "fence StreamElements uses). It has no browser storage then; what it keeps with SE_API.store "
                     "still works. Switch it off only if a widget you trust stops working with it")
        ui.select(MODES, value=safety.hosts, label="Where it may load from and send to",
                  on_change=lambda e: self._set_safety(hosts=e.value)).props("outlined dense options-dense") \
            .classes("w-full")
        self._helper_scripts(self._windows)
        if safety.hosts == "off":
            return
        ui.label("Always allowed: this toolbox, and Twitch (" + ", ".join(ALWAYS) + ").").classes("text-xs opacity-70")
        named = WidgetSafety.named(widget)
        ui.label("Hosts its code names" + ("" if named else ": none")).classes("text-sm font-semibold pt-1")
        for host in named:
            ui.switch(host, value=host not in safety.blocked,
                      on_change=lambda e, h=host: self._set_safety(
                          blocked=[b for b in safety.blocked if b != h] + ([] if e.value else [h]))) \
                .props("dense").classes("font-mono text-sm")
        ui.label("Hosts you allowed besides" + ("" if safety.extra else ": none")).classes("text-sm font-semibold pt-1")
        for host in safety.extra:
            with ui.row().classes("items-center no-wrap gap-1"):
                ui.label(host).classes("font-mono text-sm")
                ui.button(icon="close", on_click=lambda h=host: self._set_safety(
                    extra=[x for x in safety.extra if x != h])).props("flat round dense size=sm") \
                    .tooltip("Don't allow it any more")
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            more = ui.input(placeholder="allow a host, e.g. api.example.com").props("outlined dense") \
                .classes("flex-1 min-w-0")
            ui.button("Allow", on_click=lambda: self._allow(more.value or "")).props("no-caps outline dense")
        tried = {host: count for host, count in self._store.blocked(name).items()
                 if host not in safety.allowed(widget)}
        word = "would have been stopped" if safety.hosts == "report" else "were stopped"
        with ui.row().classes("items-center gap-1 pt-1"):
            ui.label(f"Tried and {word}" + ("" if tried else ": nothing so far")).classes("text-sm font-semibold")
            ui.button(icon="refresh", on_click=self._safety.refresh).props("flat round dense size=sm") \
                .tooltip("Look again")
        for host, count in sorted(tried.items()):
            with ui.row().classes("items-center no-wrap gap-2"):
                ui.label(host).classes("font-mono text-sm")
                ui.label(f"{count}×").classes("text-xs opacity-60")
                ui.button("Allow", on_click=lambda h=host: self._allow(h)).props("no-caps flat dense")
        ui.label("An allowed host counts with its subdomains. Only allow a host when you know why the widget "
                 "needs it: whatever the page knows (chat, names, its settings) can be sent there.") \
            .classes("text-xs opacity-60")

    def _helper_scripts(self, windows: ui.element) -> None:
        """The files the widget loads from StreamElements (StreamElementsMedia) and the scripts and style sheets
        its HTML loads from other servers (WidgetHelpers), and whether this PC has its own copies."""
        name = self._widget.name
        helpers, files = WidgetHelpers.named(self._widget), StreamElementsMedia.named(self._widget)
        if not helpers and not files:
            return
        kept = {**self._store.helpers(name), **self._store.streamelements_media(name)}
        ui.label("Files it loads from StreamElements and other servers").classes("text-sm font-semibold pt-1")
        for address in [*files, *helpers]:
            icon, tip = ("save", "A copy on this PC is used") if address in kept else \
                ("cloud_off", "Not on this PC: the widget shows nothing for it") if address in files else \
                ("cloud", "Loaded from that server each time")
            with ui.row().classes("items-center no-wrap gap-2 w-full"):
                ui.icon(icon, size="xs").tooltip(tip)
                ui.label(address).classes("font-mono text-xs break-all")
        with ui.row().classes("items-center gap-2"):
            ui.button("Fetch them again" if kept else "Keep them on this PC", icon="download",
                      on_click=lambda: self._keep_helpers(windows)).props("no-caps outline dense")
            if self._store.helpers(name):
                ui.button("Load helper scripts from their servers again", on_click=self._drop_helpers) \
                    .props("no-caps flat dense")
        ui.label("With a copy on this PC the widget works without StreamElements and without the internet, and "
                 "a helper script can't be changed on its server any more.").classes("text-xs opacity-60")

    async def _keep_helpers(self, windows: ui.element) -> None:
        name = self._widget.name
        with windows:
            if not await CopyFilesQuestion("Copy this widget's files to this PC?", "I may use them: copy").ask():
                return
        files, missed_files = await self._media.keep(name)
        scripts, missed = await self._helpers.keep(name)
        missed += missed_files
        count = files + scripts
        self._hub.reload(name)
        if missed:
            ui.notify(f"{count} kept on this PC; {len(missed)} couldn't be fetched: " + ", ".join(missed[:5]),
                      type="warning", multi_line=True)
        else:
            ui.notify(f"{count} file{'' if count == 1 else 's'} kept on this PC.", type="positive")
        self._safety.refresh()  # last: it removes the button this came from

    def _drop_helpers(self) -> None:
        self._helpers.drop(self._widget.name)
        self._hub.reload(self._widget.name)
        self._safety.refresh()

    def _set_safety(self, **changes: Any) -> None:
        name = self._widget.name
        self._store.set_safety(name, WidgetSafety.from_dict({**self._store.safety(name).to_dict(), **changes}))
        self._hub.reload(name)
        self._safety.refresh()

    def _allow(self, host: str) -> None:
        host = host.strip().casefold().removeprefix("https://").removeprefix("http://").split("/")[0]
        if not HOST_NAME.fullmatch(host):
            ui.notify("That's not a host name (like api.example.com)", type="warning")
            return
        safety = self._store.safety(self._widget.name)
        self._set_safety(extra=[*safety.extra, host], blocked=[b for b in safety.blocked if b != host])

    async def _clear_data(self) -> None:
        files = self._store.data_files(self._widget.name)
        kept = "store.json" in files
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-4"):
            ui.label(f"Remove everything {self._widget.name} gathered?").classes("text-lg font-semibold")
            ui.label(f"{len(files)} file{'' if len(files) == 1 else 's'}: " + ", ".join(files)).classes("text-sm")
            ui.label("What the widget's own code kept (store.json: its counters, lists, last state) is gone for "
                     "good." if kept else "Only looked-up things; they are fetched again when the widget needs "
                     "them.").classes("text-sm opacity-80")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("no-caps flat")
                ui.button("Remove", icon="delete_sweep", on_click=lambda: dialog.submit(True)) \
                    .props("no-caps unelevated color=negative")
        sure = await dialog
        dialog.delete()
        if not sure:
            return
        gone = self._store.clear_data(self._widget.name)
        self._hub.reload(self._widget.name)
        ui.notify(f"{gone} file{'' if gone == 1 else 's'} removed. The widget starts fresh.", type="positive")
        self._data.refresh()  # last: it removes the button this came from

    def _set_values(self, values: dict[str, Any]) -> None:
        # the form knows the fields that show; hidden ones keep the value they had
        values = {**self._widget.values, **values}
        self._widget = replace(self._widget, values=values)
        self._store.set_values(self._widget.name, values)
        self._hub.reload(self._widget.name)

    def _set_element(self, values: dict[str, Any]) -> None:
        """A setting of an Element changed: its settings file is the widget's JS part, which is saved again."""
        element = ElementSettings.of(self._widget)
        if element is None:  # the JS part was rewritten by hand in the meantime
            ui.notify("The JS part is no Element's settings any more: open the window again.", type="warning")
            return
        code = element.with_values(values).to_js()
        self._widget = replace(self._widget, js=code)
        self._store.save(self._widget)
        self._code["js"] = code
        self._editors["js"].set_value(code)
        self._hub.reload(self._widget.name)

    def _remove_links(self) -> None:
        """Every StreamElements address in the code now points at the toolbox; an existing widget is saved."""
        changed = 0
        for part in ("html", "css", "js"):
            code, count = without_streamelements_links(self._code[part])
            if count:
                changed += count
                self._code[part] = code
                self._editors[part].set_value(code)
        if not changed:
            ui.notify("There are no StreamElements links in this code.")
            return
        ui.notify(f"{changed} StreamElements link{'s' if changed > 1 else ''} now point{'' if changed > 1 else 's'} "
                  "at the toolbox.", type="positive")
        if self._widget:
            self._save()

    def _save(self) -> None:
        try:
            name = self._widget.name if self._widget else check_name(self._name.value or "")
            if not self._widget and self._store.get(name):
                raise ValueError(f"there's a widget {name!r} already")
            fields = parse_fields(self._code["fields"])
        except ValueError as e:
            ui.notify(str(e), type="warning", multi_line=True)
            return
        saved = Widget(name, self._code["html"], self._code["css"], self._code["js"], fields,
                       self._widget.values if self._widget else {}, self._widget.frame if self._widget else {})
        self._store.save(saved)
        self._on_saved()
        if self._widget:
            self._widget = saved
            self._hub.reload(name)
            ui.notify("Saved. Open the window again to see new settings fields.", type="positive")
        else:
            ui.notify(f"Widget {name} made", type="positive")
            self._dialog.close()
