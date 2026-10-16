from nicegui import ui

from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.gui.components.alerts_tool.alerts_tool import AlertsTool
from streamer_toolbox.gui.components.keep_typed import keep_typed
from streamer_toolbox.gui.components.overlay_source import OverlaySource
from streamer_toolbox.gui.components.widgets_tool.widgets_tool import WidgetsTool

SOURCE_NAME = "toolbox alerts"  # the Browser source "Add it to OBS" makes


class OverlayPage:
    """Overlay: what the toolbox shows on stream through a Browser source in OBS. /overlays is the main view:
    a card each for Alerts and Widgets. /overlays?show=alerts is the alerts: the alerts overlay itself (its
    address, whether OBS is listening, Add it to OBS), their preview and the alerts; ?show=widgets the widgets
    (custom widget code in StreamElements' format, each its own Browser source); the side menu lists both."""

    def __init__(self, alerts: AlertsTool, widgets: WidgetsTool, queue: AlertQueue, source: OverlaySource,
                 port: int) -> None:
        self._alerts = alerts
        self._widgets = widgets
        self._queue = queue
        self._source = source
        self._address = f"http://127.0.0.1:{port}/overlay/alerts"

    def build(self) -> None:
        show = ui.context.client.request.query_params.get("show", "")
        if show == "alerts":
            self._back()
            with ui.card().classes("w-full max-w-3xl gap-2"):
                self._overlay()
            with ui.card().classes("w-full max-w-3xl gap-2"):
                self._preview()
            self._alerts.build()
        elif show == "widgets":
            self._back()
            self._widgets.build()
        else:
            self._overview()

    @staticmethod
    def _back() -> None:
        ui.link("← Overlay", "/overlays").classes("text-sm")

    def _overview(self) -> None:
        with ui.element("div").classes("grid gap-3 w-full sm:grid-cols-2 items-stretch"):
            self._tile("campaign", "Alerts", "alerts", "What shows for a follow, sub, resub, gift, cheer, raid "
                                                       "or tip: text, picture, sound, a preview to test them, "
                                                       "and their Browser source for OBS")
            self._tile("widgets", "Widgets", "widgets", "Custom widget code in StreamElements' format, each with "
                                                        "its own Browser source")

    @staticmethod
    def _tile(icon: str, title: str, show: str, note: str) -> None:
        with ui.link(target=f"/overlays?show={show}").classes("no-underline text-inherit"), \
                ui.card().classes("w-full h-full gap-1 cursor-pointer hover:bg-gray-500/10"):
            with ui.row().classes("items-center no-wrap gap-2 w-full"):
                ui.icon(icon).classes("text-2xl text-primary")
                ui.label(title).classes("text-lg font-semibold flex-1")
            ui.label(note).classes("text-xs opacity-70")

    def _overlay(self) -> None:
        ui.label("The alerts overlay in OBS").classes("text-lg font-semibold")
        ui.label("One Browser source shows every alert. Add it once to each scene that should have alerts (the "
                 "same source can go into many scenes). Widgets have their own addresses, under Overlay → "
                 "Widgets.") \
            .classes("text-sm opacity-80")
        with ui.row().classes("items-center gap-2"):
            ui.label(self._address).classes("font-mono text-sm break-all")
            ui.button(icon="content_copy", on_click=lambda: (ui.clipboard.write(self._address),
                                                            ui.notify("Address copied"))) \
                .props("flat round dense").tooltip("Copy the address")
        self._listening()
        ui.timer(3.0, self._listening.refresh)
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            scene = keep_typed(ui.select([], label="Scene", new_value_mode="add-unique")
                               .props("outlined dense options-dense").classes("flex-1 min-w-0"))
            ui.button("Add it to OBS", icon="add_to_queue",
                      on_click=lambda: self._source.add(scene.value, SOURCE_NAME, self._address)) \
                .props("no-caps unelevated").tooltip("Makes the Browser source in that scene, as big as your canvas")
        ui.label("By hand: Sources → + → Browser, the address above, width and height of your canvas, tick "
                 "\"Control audio via OBS\". Add ?at=center or ?at=bottom to the address to move the alerts. "
                 "The look: the source's Custom CSS, e.g. :root { --alert-accent: #ffb347; --alert-size: 56px; }") \
            .classes("text-xs opacity-60")
        ui.timer(0.1, lambda: self._load_scenes(scene), once=True)

    async def _load_scenes(self, scene: ui.select) -> None:
        scene.set_options(await self._source.scenes())  # empty with OBS off: the scene can still be typed

    @ui.refreshable_method
    def _listening(self) -> None:
        count = self._queue.overlays
        text = "OBS isn't showing the overlay yet: alerts would play to nobody." if not count \
            else f"{count} Browser source{'s are' if count > 1 else ' is'} showing it."
        ui.label(text).classes("text-sm " + ("text-warning" if not count else "text-positive"))

    def _preview(self) -> None:
        ui.label("Preview").classes("text-lg font-semibold")
        ui.label("Test alerts show here too, also without OBS. Sound may stay silent here until you clicked "
                 "something on this page (browsers want that); in OBS it plays.").classes("text-sm opacity-80")
        # the page shrinks itself to the frame (?preview), so the frame can be as wide as the card
        with ui.element("div").classes("w-full rounded overflow-hidden border border-gray-500/30") \
                .style("aspect-ratio: 16 / 9; "
                       "background: repeating-conic-gradient(#2a2a2a 0% 25%, #1c1c1c 0% 50%) 0 0 / 24px 24px"):
            ui.element("iframe").props("src=/overlay/alerts?preview=1") \
                .style("width: 100%; height: 100%; border: 0; display: block; "
                       "color-scheme: light")  # else a dark page paints the frame white
