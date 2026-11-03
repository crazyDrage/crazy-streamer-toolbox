from nicegui import ui

from streamer_toolbox.core.event_types.event_flows import EventFlows
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_users import EventUsers

FIELD = "outlined dense options-dense"


class WidgetEventsTab:
    """A widget's Events tab (his round 78: widgets pick event types instead of their own inputs): the event
    types it gets, each with what its code hears it as, its values, and the flows that send it (or Make its
    flow). The event types themselves are set in Overlay → Events. Every change is saved at once."""

    def __init__(self, events: EventTypeStore, users: EventUsers, flows: EventFlows, widget: str) -> None:
        self._events = events
        self._users = users
        self._flows = flows
        self._widget = widget

    def give(self, widget: str) -> None:
        """A widget was just made: it gets the events its code listens for."""
        self._widget = widget
        self._users.give_events(widget)

    @ui.refreshable_method
    def build(self) -> None:
        ui.label("What this widget gets: the events a flow sends (Overlay → Events). Its code gets each in "
                 "onEventReceived, as the listener it hears it as.").classes("text-xs opacity-60")
        picked = list(self._users.events_of(self._widget))
        options = {t.name: t.name for t in self._events.all()}
        options.update({name: f"{name} (gone)" for name in picked if name not in options})
        with ui.row().classes("items-center gap-2 w-full"):
            ui.select(options, multiple=True, value=picked, label="Events it gets", on_change=self._picked) \
                .props(FIELD + " use-chips").classes("flex-1 min-w-[14rem]")
            ui.button("From its code", icon="code", on_click=self._from_code).props("no-caps outline dense") \
                .tooltip("The events its code listens for ('follower-latest', 'message', ...)")
        for name in picked:
            self._card(name)
        if not picked:
            ui.label("No events: nothing reaches this widget.").classes("text-sm text-warning")
        ui.link("Change the events and their values: Overlay → Events", "/overlays?show=events").classes("text-xs")

    def _card(self, name: str) -> None:
        kind = self._events.get(name)
        with ui.card().props("flat bordered").classes("w-full gap-1 p-2"):
            ui.label(name).classes("font-semibold")
            if kind is None:
                ui.label("This event isn't there any more: take it away or make it again in Overlay → Events.") \
                    .classes("text-xs text-warning")
                return
            ui.label(f"Its code hears it as: {kind.listener}").classes("text-xs opacity-70")
            ui.label("Values: " + (", ".join(v.name for v in kind.values) or "none")).classes("text-xs opacity-60")
            sending = self._flows.sending(name)
            reached = [label for label, only_to in sending if only_to in ("", f"widget {self._widget}")]
            with ui.row().classes("items-center gap-2"):
                if reached:
                    ui.label("Sent by: " + ", ".join(reached)).classes("text-xs text-positive")
                else:
                    ui.label("No flow sends it to this widget yet.").classes("text-xs text-warning")
                    ui.button("Make its flow", icon="account_tree", on_click=lambda: self._make_flow(name)) \
                        .props("no-caps outline dense") \
                        .tooltip("In the folder Events: on every such event → Send " + name + ", to every widget "
                                 "and alert that uses it")

    def _picked(self, e) -> None:
        made = self._users.set_widget_events(self._widget, tuple(e.value or ()))
        if made:
            ui.notify(f"Flow made in the folder Events: {', '.join(made)}", type="positive")
        self.build.refresh()

    def _from_code(self) -> None:
        found = self._users.in_code(self._widget)
        if not found:
            ui.notify("Its code names no event the toolbox knows ('follower-latest', 'message', ...)")
            return
        made = self._users.set_widget_events(self._widget, (*self._users.events_of(self._widget), *found))
        ui.notify(f"It gets {', '.join(found)}" + (f"; flows made: {', '.join(made)}" if made else ""),
                  type="positive")
        self.build.refresh()

    def _make_flow(self, name: str) -> None:
        kind = self._events.get(name)
        if kind is not None:
            ui.notify(f"Flow made in the folder Events: {self._flows.make(kind)}", type="positive")
        self.build.refresh()
