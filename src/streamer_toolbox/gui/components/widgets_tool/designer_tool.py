from nicegui import ui

from streamer_toolbox.core.event_types.event_users import EventUsers
from streamer_toolbox.core.widgets.element_design import HTML, ElementDesign
from streamer_toolbox.core.widgets.widget import Widget, check_name
from streamer_toolbox.core.widgets.widget_hub import WidgetHub
from streamer_toolbox.core.widgets.widget_store import WidgetStore
from streamer_toolbox.gui.components.widgets_tool.widget_designer import WidgetDesigner, address


class DesignerTool:
    """Overlay → Widget editor (a sub row of Widgets, his "separate sub tab"): the widgets made of pieces
    (ElementDesign: made here, or StreamElements Elements imported), a New one, and one widget's editor
    (WidgetDesigner) at ?show=designer&widget=<name>. A widget made here is an ordinary widget: Overlay → Widgets
    lists it with its address for OBS."""

    def __init__(self, store: WidgetStore, hub: WidgetHub, users: EventUsers) -> None:
        self._store = store
        self._hub = hub
        self._users = users

    def build(self) -> None:
        with ui.card().classes("w-full gap-1"):
            ui.label("Widget editor").classes("text-lg font-semibold")
            ui.label("Make a widget without code: pictures and GIFs, videos, texts that fill in (latest follower, "
                     "subs this stream, ...) and alerts for follows, subs, cheers, raids and tips, with their "
                     "animations and sounds. Each is a widget with its own Browser source (Overlay → Widgets).") \
                .classes("text-sm opacity-80")
            with ui.row().classes("items-center no-wrap gap-2 w-full pt-1"):
                name = ui.input(placeholder="Name of a new one, e.g. follower_bar").props("outlined dense") \
                    .classes("flex-1 min-w-0 max-w-sm")
                ui.button("New widget", icon="add", on_click=lambda: self._new(name.value or "")) \
                    .props("no-caps unelevated")
                name.on("keydown.enter", lambda: self._new(name.value or ""))
        found = [widget for widget in map(self._store.get, self._store.names())
                 if widget is not None and ElementDesign.of(widget) is not None]
        if not found:
            ui.label("No widgets made here yet. StreamElements Elements you import (Overlay → Import) show up here "
                     "too.").classes("opacity-70")
        for widget in found:
            design = ElementDesign.of(widget)
            count = sum(len(design.pieces(number)) for number, _ in design.layers())
            alerts = [title for number, title in design.layers() if design.event_of(number)]
            with ui.card().classes("w-full"), ui.row().classes("items-center no-wrap w-full gap-2"):
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label(widget.name).classes("text-lg font-semibold")
                    ui.label(f"{count} piece{'' if count == 1 else 's'}"
                             + (": " + ", ".join(alerts) if alerts else "")).classes("text-xs opacity-70")
                ui.button("Edit", icon="design_services").props(f"no-caps unelevated href={address(widget.name)}")
                ui.button(icon="tune").props(f"flat round dense href=/overlays?show=widgets&widget={widget.name}") \
                    .tooltip("Its widget page: OBS address, events, code")

    def _new(self, name: str) -> None:
        try:
            name = check_name(name)
            if self._store.get(name) is not None:
                raise ValueError(f"there's a widget {name!r} already")
        except ValueError as error:
            ui.notify(str(error), type="warning")
            return
        self._store.save(Widget(name, html=HTML, js=ElementDesign.new().to_js(), events=()))
        ui.navigate.to(address(name))

    def build_editor(self, name: str) -> None:
        ui.link("← Widget editor", "/overlays?show=designer").classes("text-sm")
        widget = self._store.get(name)
        design = ElementDesign.of(widget) if widget is not None else None
        if widget is None:
            ui.label(f"There is no widget {name!r} (any more).").classes("opacity-70")
            return
        if design is None:
            ui.label(f"{name} is a widget with its own code: change it on its widget page.").classes("opacity-70")
            ui.button("Its widget page", icon="tune").props(f"no-caps outline href=/overlays?show=widgets&widget={name}")
            return
        WidgetDesigner(self._store, self._hub, self._users, widget, design).build()
