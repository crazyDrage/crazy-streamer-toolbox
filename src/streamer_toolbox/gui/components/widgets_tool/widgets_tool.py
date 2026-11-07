from nicegui import ui

from streamer_toolbox.core.widgets.element_design import ElementDesign
from streamer_toolbox.core.widgets.streamelements_fallback import StreamElementsFallback
from streamer_toolbox.core.event_types.event_flows import EventFlows
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_users import EventUsers
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore
from streamer_toolbox.gui.components.overlay_source import OverlaySource
from streamer_toolbox.gui.components.widgets_tool.widget_editor import WidgetEditor
from streamer_toolbox.gui.components.widgets_tool.widget_events_tab import WidgetEventsTab
from streamer_toolbox.gui.components.widgets_tool.widget_editor import address as editor_address
from streamer_toolbox.gui.components.widgets_tool.widget_designer import address as designer_address


class WidgetsTool:
    """The Widgets part of the Overlay page: custom widgets in StreamElements' format (the HTML / CSS / JS / FIELDS
    people share), each with its own overlay address for a Browser source. A row per widget: whether OBS shows it,
    its address, Open (its own page: WidgetEditor, build_editor), Add it to OBS, Delete. Importing them from StreamElements or
    another program is Overlay → Import (his round 64: the import apart, its result handed to Widgets)."""

    def __init__(self, store: WidgetStore, hub: WidgetHub, source: OverlaySource, port: int, events: EventTypeStore,
                 users: EventUsers, flows: EventFlows,
                 fallback: StreamElementsFallback | None = None) -> None:
        self._events = events
        self._users = users
        self._flows = flows
        self._fallback = fallback
        self._store = store
        self._hub = hub
        self._source = source
        self._port = port

    def build(self) -> None:
        with ui.card().classes("w-full gap-1"):
            ui.label("Custom widgets").classes("text-lg font-semibold")
            ui.label("Widget code made for StreamElements (HTML, CSS, JS, FIELDS) runs here: a new widget starts with "
                     "short code to read and change, or paste the four parts. The toolbox gives the code what StreamElements would: follows, subs, gifts, cheers, "
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
            ui.button("New widget", icon="add").props(f"no-caps outline href={editor_address(None)}") \
                .tooltip("A widget with its own code (HTML, CSS, JS)")
            ui.button("Widget editor", icon="design_services").props("no-caps outline href=/overlays?show=designer") \
                .tooltip("Make one without code: pictures, GIFs, texts, alerts")
            ui.button("Add the example", icon="school", on_click=self._add_example).props("no-caps flat") \
                .tooltip("A small widget to try and to read: latest follower and chat lines")
            ui.button("Import ...", icon="file_download").props("no-caps flat href=/overlays?show=import")                 .tooltip("From StreamElements (your overlays and Elements) or another program: Overlay → Import")

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
                widget = self._store.get(name)
                if widget is not None and ElementDesign.of(widget) is not None:
                    ui.button("Edit", icon="design_services") \
                        .props(f"no-caps outline href={designer_address(name)}").tooltip("In the widget editor")
                ui.button("Open", icon="tune").props(f"no-caps unelevated href={editor_address(name)}") \
                    .tooltip("Preview, settings, test events and its code")
                ui.button("Add it to OBS", icon="add_to_queue", on_click=lambda n=name: self._add_to_obs(windows, n)) \
                    .props("no-caps outline")
                ui.button(icon="delete", on_click=lambda n=name: self._delete(windows, n)).props("flat round dense") \
                    .tooltip("Delete this widget")

    def _add_example(self) -> None:
        name = self._store.add_example()
        self._users.give_events(name)  # its chat and follow events, their flows made once (his round 78)
        self._rows.refresh()
        ui.notify(f"{name} is in the list: Open shows it", type="positive")

    def build_editor(self, name: str) -> None:
        """One widget's own page (WidgetEditor); "new" = a new one."""
        ui.link("← Widgets", "/overlays?show=widgets").classes("text-sm")
        widget = None if name == "new" else self._store.get(name)
        if name != "new" and widget is None:
            ui.label(f"There is no widget {name!r} (any more).").classes("opacity-70")
            return
        WidgetEditor(self._store, self._hub, widget,
                     WidgetEventsTab(self._events, self._users, self._flows, widget.name if widget else "")).build()

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
            with windows:  # the rows are drawn again every few seconds: the button this came from may be gone
                ui.notify(f"Widget {name} deleted")
            self._rows.refresh()
