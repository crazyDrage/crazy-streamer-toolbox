import re
from dataclasses import replace
from pathlib import PureWindowsPath

from nicegui import ui

from streamer_toolbox.core.alerts import alert_starters
from streamer_toolbox.core.alerts.alert_queue import AlertQueue
from streamer_toolbox.core.alerts.alert_rule import AlertRule
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.event_types.event_flows import ONLY_TO, action_name
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_users import EventUsers
from streamer_toolbox.core.event_types.event_value import EventValue
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.gui.components.alerts_tool.alert_editor import AlertEditor

FIELD = "outlined dense options-dense"
NEW_EVENT = "+"  # "+ New alert": a new event type for it, named like the alert
# what a new alert on one of the usual events says at first ("{user} just followed!")
STARTER_TEXTS = {event: text for event, (_, text, _, _) in alert_starters.STARTERS.items()}


def address(id_: str) -> str:
    """An alert's page in the toolbox."""
    return f"/overlays?show=alerts&alert={id_}"


class AlertsTool:
    """The Alerts part of the Overlay page: his list of alerts (his round 65), one short block each: on / off,
    its name, what it says and shows, the event it plays on and the flows that send it, Test, and Settings (its
    own page with everything: AlertEditor, build_editor). "+ New alert": a name and its event (his round 78)."""

    def __init__(self, store: AlertStore, queue: AlertQueue, flows: FlowLibrary, events: EventTypeStore,
                 users: EventUsers) -> None:
        self._store = store
        self._queue = queue
        self._flows = flows
        self._events = events
        self._users = users

    def build(self) -> None:
        with ui.row().classes("items-center w-full gap-2"):
            ui.label("Each alert plays on an event (Overlay → Events): the event's flow, in the folder Events, "
                     "sends it on a follow, sub, ...; change those like any flow.").classes("text-sm opacity-80 flex-1")
            ui.button("New alert", icon="add", on_click=self._new).props("no-caps unelevated")
        self._list()

    @ui.refreshable_method
    def _list(self) -> None:
        with ui.element("div").classes("grid gap-3 w-full md:grid-cols-2 xl:grid-cols-3 items-start"):
            for rule in self._store.all():
                self._rule(rule.id)

    def _rule(self, id_: str) -> None:
        rule = self._store.get(id_)
        with ui.card().classes("w-full gap-1"):
            with ui.row().classes("items-center no-wrap w-full gap-2"):
                ui.switch(value=rule.on, on_change=lambda e: self._store.save(
                    replace(self._store.get(id_), on=e.value))).props("dense") \
                    .tooltip("Off: its box shows nothing (the flows still run)")
                self._title(id_)
                ui.button("Test", icon="play_arrow", on_click=lambda: self._test(id_)) \
                    .props("no-caps outline dense").tooltip("Shows this alert now with its examples")
                ui.button("Settings", icon="tune").props(f"no-caps unelevated dense href={address(id_)}").tooltip("Name, event, text, picture, sound, where the "
                                                               "words sit, animations: with a preview")
            self._summary(id_)

    @ui.refreshable_method
    def _title(self, id_: str) -> None:
        rule = self._store.get(id_)
        ui.label(rule.title if rule else "").classes("text-lg font-semibold flex-1 min-w-0 break-words")

    @ui.refreshable_method
    def _summary(self, id_: str) -> None:
        """What the alert says and shows, and what starts it, in three small lines."""
        rule = self._store.get(id_)
        if rule is None:
            return
        ui.label(rule.text or "(no text)").classes("text-sm break-all")
        ui.label(summary(rule)).classes("text-xs opacity-60 break-all")
        send, only = action_name(rule.event), {"", f"alert {rule.id}"}
        users = [f.label for f in self._flows.all() if any(
            n.action == send and str(n.params.get(ONLY_TO) or "") in only for n in f.nodes)]
        ui.label(f"Plays on the event: {rule.event}" if rule.event else "It plays on no event: pick one in Settings") \
            .classes("text-xs " + ("opacity-60" if rule.event else "text-warning"))
        if users:
            ui.label("Sent by: " + ", ".join(users)).classes("text-xs opacity-60 break-words")
        elif rule.event:
            ui.label(f"No flow sends {rule.event} to it yet: Overlay → Events.").classes("text-xs text-warning")

    def build_editor(self, id_: str) -> None:
        """One alert's own page (AlertEditor)."""
        ui.link("← Alerts", "/overlays?show=alerts").classes("text-sm")
        if self._store.get(id_) is None:
            ui.label("This alert isn't there (any more).").classes("opacity-70")
            return
        AlertEditor(self._store, self._queue, self._events, self._users, id_).build()

    async def _test(self, id_: str) -> None:
        rule = self._store.get(id_)
        try:
            in_front = await self._queue.show(rule.alert_for(rule.examples()))
        except Exception as e:  # a picture or sound that isn't there
            ui.notify(str(e), type="negative", multi_line=True)
            return
        where = "showing now" if not in_front else f"{in_front} in front of it"
        note = "" if self._queue.overlays else " (in the preview only: OBS isn't showing the overlay)"
        ui.notify(f"{rule.title} test alert: {where}{note}", type="positive")

    def _new(self) -> None:
        """A name and the event it plays on (his round 78); the event's flow is made once, if it has none."""
        events = {t.name: t.name for t in self._events.all()}
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-3"):
            ui.label("New alert").classes("text-lg font-semibold")
            name = ui.input("Name", placeholder="e.g. Lizard redeem").props(FIELD + " autofocus").classes("w-full")
            start = ui.select({NEW_EVENT: "A new event, named like the alert", **events}, value=NEW_EVENT,
                              label="It plays on the event").props(FIELD).classes("w-full")
            ui.label("A follow, sub, ...: its flow (in the folder Events) sends it to every alert and widget that "
                     "uses it. A new event gets its values in Overlay → Events.").classes("text-xs opacity-60")

            def make() -> None:
                event = start.value or NEW_EVENT
                title = (name.value or "").strip() or (event.capitalize() if event != NEW_EVENT else "New alert")
                if event == NEW_EVENT:
                    event = self._events.add(re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_-") or "event",
                                             (EventValue("user", "TestViewer"),)).name
                rule, made = self._users.new_alert(title, event, STARTER_TEXTS.get(event, ""))
                dialog.close()
                if made:
                    ui.notify(f"Flow made in the folder Events: {', '.join(made)}", type="positive")
                ui.navigate.to(address(rule.id))

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("no-caps flat")
                ui.button("Make it", icon="check", on_click=make).props("no-caps unelevated")
        dialog.open()


def summary(rule: AlertRule) -> str:
    """"party.gif · ding.ogg · 5 s · on the picture: name, amount" / "no picture · no sound · 5 s"."""
    on_picture = [part.title.casefold() for part in rule.parts if part.on_picture]
    # PureWindowsPath reads both \ and /: an alert set up on Windows shows the same on Linux
    bits = [PureWindowsPath(rule.image).name if rule.image else "no picture",
            PureWindowsPath(rule.sound).name if rule.sound else "no sound", f"{rule.seconds:g} s"]
    if on_picture:
        bits.append("on the picture: " + ", ".join(on_picture))
    if rule.variations:
        bits.append(f"{len(rule.variations)} bigger alert{'s' if len(rule.variations) > 1 else ''}")
    return " · ".join(bits)
