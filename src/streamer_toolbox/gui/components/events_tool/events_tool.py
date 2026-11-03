from dataclasses import replace

from nicegui import app, ui

from streamer_toolbox.core.event_types.event_flows import EventFlows
from streamer_toolbox.core.event_types.event_type import EventType
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_users import EventUsers
from streamer_toolbox.core.event_types.event_value import KINDS, EventValue, names_in
from streamer_toolbox.gui.components.app_shell import SHOW_ALL_KEY

FIELD = "outlined dense options-dense"
# what the default field shows for each kind while it is empty
EXAMPLES = {"text": "e.g. Kit", "number": "e.g. 5", "colour": "e.g. #ffb347", "yes_no": "true or false",
            "picture": "a file or web address", "sound": "a file or web address"}


class EventsTool:
    """The Events part of the Overlay page (his round 78): the event types widgets and alerts get their data
    from. A block per type that folds open: its name, its values (name, default, kind, the names other programs
    read it as), the names other programs hear the type as, and who uses and sends it. The default types stay
    hidden until something uses them; "Show everything" (top right) shows them, each with its eye. Every change
    is saved at once."""

    def __init__(self, store: EventTypeStore, users: EventUsers, flows: EventFlows) -> None:
        self._store = store
        self._users = users
        self._flows = flows
        self._open: set[str] = set()  # the blocks folded open, so a redraw keeps them open
        self._search = ""

    def build(self) -> None:
        with ui.card().classes("w-full max-w-3xl gap-1"):
            ui.label("Events").classes("text-lg font-semibold")
            ui.label("What widgets and alerts show: a follow, a sub, a chat message, or one you make. Each event "
                     "has values (the viewer's name, an amount, a colour ...). A flow sends it; every widget and "
                     "alert that uses it gets it.").classes("text-sm opacity-80")
            ui.label("\"Also known as\": the names a StreamElements widget's code uses (follower-latest, name), so "
                     "an imported widget is connected by itself.").classes("text-xs opacity-60")
        with ui.row().classes("items-center gap-2 w-full max-w-3xl"):
            ui.button("New event", icon="add", on_click=self._add).props("no-caps outline")
            ui.input(placeholder="Search", value=self._search, on_change=self._searched) \
                .props(FIELD + " clearable debounce=300").classes("flex-1 min-w-[10rem]") \
                .tooltip("An event's name, a value's name or an \"also known as\" name")
        self._list()
        showing = [self._show_all()]

        def follow_the_eye() -> None:  # the eye on the top right redraws the menus, not this page
            if self._show_all() != showing[0]:
                showing[0] = self._show_all()
                self._list.refresh()

        ui.timer(1.0, follow_the_eye)

    @staticmethod
    def _show_all() -> bool:
        return bool(app.storage.general.get(SHOW_ALL_KEY, False))

    def _searched(self, e) -> None:
        self._search = (e.value or "").strip().casefold()
        self._list.refresh()

    def _found(self, kind: EventType) -> bool:
        if not self._search:
            return True
        names = [kind.name, *kind.also_known_as] + [n for v in kind.values for n in (v.name, *v.also_known_as)]
        return any(self._search in n.casefold() for n in names)

    @ui.refreshable_method
    def _list(self) -> None:
        show_all = self._show_all()
        found = [t for t in self._store.all() if self._found(t)]
        shown = [t for t in found if show_all or not t.hidden]
        with ui.column().classes("w-full max-w-3xl gap-2"):
            for kind in shown:
                self._block(kind)
            hidden = len(found) - len(shown)
            if hidden:
                ui.label(f"{hidden} more {'is' if hidden == 1 else 'are'} hidden until something uses "
                         f"{'it' if hidden == 1 else 'them'} (the ones that come with the toolbox). \"Show "
                         f"everything\" on the top right shows them.").classes("text-xs opacity-60")
            elif not shown:
                ui.label("No event matches." if self._search else "No events yet.").classes("opacity-70")

    def _block(self, kind: EventType) -> None:
        name = kind.name
        with ui.card().props("flat bordered").classes("w-full p-0 gap-0" + (" opacity-70" if kind.hidden else "")):
            fold = ui.expansion(value=name in self._open,
                                on_value_change=lambda e: (self._open.add if e.value else self._open.discard)(name)) \
                .classes("w-full")
            with fold.add_slot("header"), \
                    ui.row().classes("items-center no-wrap gap-2 w-full min-w-0 overflow-hidden"):
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label(name).classes("font-semibold")
                    ui.label(", ".join(v.name for v in kind.values) or "no values yet") \
                        .classes("text-xs opacity-60 truncate w-full")
                if self._show_all():
                    ui.button(icon="visibility_off" if kind.hidden else "visibility").props("flat round dense") \
                        .on("click.stop.prevent", lambda: self._save(name, replace(kind, hidden=not kind.hidden))) \
                        .tooltip("Show it again" if kind.hidden else "Hide it")
                ui.button(icon="delete").props("flat round dense") \
                    .on("click.stop.prevent", lambda: self._delete(name)).tooltip("Delete this event")
            with fold, ui.column().classes("w-full gap-2"):
                self._fields(kind)

    def _fields(self, kind: EventType) -> None:
        name = kind.name
        box = ui.input("Name", value=name).props(FIELD).classes("w-full") \
            .tooltip(f"Its box in flows: \"Send {name}\" (Add box → Event). A new name: the widgets, alerts "
                     "and flows that use it follow")
        box.on("blur", lambda: self._rename(name, box.value or ""))
        box.on("keydown.enter", lambda: self._rename(name, box.value or ""))
        ui.label("Values").classes("text-sm font-semibold")
        for index, value in enumerate(kind.values):
            self._value_row(name, index, value)
        ui.button("Add value", icon="add", on_click=lambda: self._add_value(name)).props("no-caps flat dense")
        ui.input("Also known as", value=", ".join(kind.also_known_as), placeholder="e.g. follower-latest",
                 on_change=lambda e: self._change(name, also_known_as=names_in(e.value or ""))) \
            .props(FIELD + " debounce=500").classes("w-full") \
            .tooltip("The names other programs' code hears this event as (StreamElements: onEventReceived's "
                     "listener); more than one with commas")
        users = self._users.users(name)
        ui.label("Used by: " + (", ".join(users) or "nothing yet (a widget's Events tab, an alert's Settings)")) \
            .classes("text-xs opacity-60 break-words")
        sending = self._flows.sending(name)
        with ui.row().classes("items-center gap-2"):
            if sending:
                ui.label("Sent by: " + ", ".join(label + (f" (only to {only_to})" if only_to else "")
                                                 for label, only_to in sending)).classes("text-xs opacity-60 break-words")
            else:
                ui.label("No flow sends it yet.").classes("text-xs " + ("text-warning" if users else "opacity-60"))
            if not sending or self._users.unreached(name):
                ui.button("Make its flow", icon="account_tree", on_click=lambda: self._make_flow(name)) \
                    .props("no-caps outline dense") \
                    .tooltip("In the folder Events: " + (f"on every {name} → Send {name}" if kind.default else
                                                         f"its Start box → Send {name}; you fill its values")
                             + ", to every widget and alert that uses it")
        unreached = self._users.unreached(name) if sending else []
        if unreached:
            ui.label("No flow sends it to: " + ", ".join(unreached)).classes("text-xs text-warning")

    def _value_row(self, name: str, index: int, value: EventValue) -> None:
        # two halves side by side, one over the other on a phone (the delete stays with its value)
        with ui.row().classes("items-center gap-2 w-full"):
            with ui.row().classes("items-center no-wrap gap-2 flex-1 min-w-[16rem]"):
                box = ui.input("Value", value=value.name).props(FIELD).classes("flex-1 min-w-0")
                box.on("blur", lambda: self._rename_value(name, index, box.value or ""))
                box.on("keydown.enter", lambda: self._rename_value(name, index, box.value or ""))
                ui.input("Default", value=value.default, placeholder=EXAMPLES[value.kind],
                         on_change=lambda e: self._change_value(name, index, default=e.value or "")) \
                    .props(FIELD + " debounce=500").classes("flex-1 min-w-0") \
                    .tooltip("What it is when the flow gives nothing")
            with ui.row().classes("items-center no-wrap gap-2 flex-1 min-w-[16rem]"):
                self._value_end(name, index, value)

    def _value_end(self, name: str, index: int, value: EventValue) -> None:
        ui.select(KINDS, value=value.kind, label="Kind",
                  on_change=lambda e: self._change_value(name, index, refresh=True, kind=e.value)) \
            .props(FIELD).classes("w-28 shrink-0")
        ui.input("Also known as", value=", ".join(value.also_known_as), placeholder="e.g. name",
                 on_change=lambda e: self._change_value(name, index, also_known_as=names_in(e.value or ""))) \
            .props(FIELD + " debounce=500").classes("flex-1 min-w-0") \
            .tooltip("The names other programs' code reads this value as (StreamElements: "
                     "obj.detail.event.<name>)")
        ui.button(icon="delete", on_click=lambda: self._drop_value(name, index)).props("flat round dense") \
            .tooltip("Take this value away")

    def _save(self, old_name: str, changed: EventType, refresh: bool = True) -> bool:
        try:
            self._store.save(old_name, changed)
        except ValueError as e:
            ui.notify(str(e), type="warning")
            self._list.refresh()
            return False
        if refresh:
            self._list.refresh()
        return True

    def _change(self, name: str, **values) -> None:
        found = self._store.get(name)
        if found:  # typing stays in its field: no redraw
            self._save(name, replace(found, **values), refresh=False)

    def _values(self, name: str, values: tuple[EventValue, ...], refresh: bool = True) -> None:
        found = self._store.get(name)
        if found:
            self._save(name, replace(found, values=values), refresh)

    def _change_value(self, event: str, index: int, refresh: bool = False, **changes) -> None:
        found = self._store.get(event)
        if found:  # event, not name: a value's new name comes in changes
            self._values(event, tuple(replace(v, **changes) if n == index else v
                                     for n, v in enumerate(found.values)), refresh)

    def _add_value(self, name: str) -> None:
        found = self._store.get(name)
        if not found:
            return
        taken = {v.name for v in found.values}
        value, number = "value", 2
        while value in taken:
            value, number = f"value{number}", number + 1
        self._values(name, (*found.values, EventValue(value)))

    def _drop_value(self, name: str, index: int) -> None:
        found = self._store.get(name)
        if found:
            self._values(name, tuple(v for n, v in enumerate(found.values) if n != index))

    def _rename_value(self, name: str, index: int, typed: str) -> None:
        """Through EventUsers: {old} in its alerts' words and the Send boxes' field follow."""
        found = self._store.get(name)
        if not found or typed.strip() == found.values[index].name:
            return
        try:
            self._users.rename_value(name, found.values[index].name, typed.strip())
        except ValueError as e:
            ui.notify(str(e), type="warning")
        self._list.refresh()

    def _rename(self, name: str, typed: str) -> None:
        """Through EventUsers: the widgets, alerts and flows that use it follow."""
        new = typed.strip()
        if self._store.get(name) is None or new == name:
            return
        try:
            self._users.rename_event(name, new)
        except ValueError as e:
            ui.notify(str(e), type="warning")
            self._list.refresh()
            return
        if name in self._open:
            self._open.discard(name)
            self._open.add(new)
        self._list.refresh()

    def _make_flow(self, name: str) -> None:
        kind = self._store.get(name)
        if kind is not None:
            ui.notify(f"Flow made in the folder Events: {self._flows.make(kind)}", type="positive")
            self._list.refresh()

    def _add(self) -> None:
        made = self._store.add()
        self._open.add(made.name)
        self._list.refresh()
        ui.notify(f"{made.name} is last in the list: give it a name and its values", type="positive")

    async def _delete(self, name: str) -> None:
        found = self._store.get(name)
        if not found:
            return
        with ui.dialog() as dialog, ui.card().classes("w-96 gap-3"):
            ui.label(f"Delete the event {name}?").classes("text-lg font-semibold")
            values = ", ".join(v.name for v in found.values)
            ui.label(f"Its values ({values or 'none'}) and its other names go"
                     + (". It came with the toolbox and doesn't come back by itself; New event makes it again."
                        if found.default else ".")).classes("text-sm opacity-80")
            users, sending = self._users.users(name), self._flows.sending(name)
            if users or sending:
                ui.label("Used by " + (", ".join(users) or "nothing") + f"; {len(sending)} Send box"
                         + ("es" if len(sending) != 1 else "") + " in flows. They stay, and say the event is "
                         "missing.").classes("text-sm text-warning")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: dialog.submit(False)).props("flat no-caps")
                ui.button("Delete", on_click=lambda: dialog.submit(True)).props("unelevated no-caps color=negative")
        sure = await dialog
        dialog.delete()
        if sure:
            self._store.delete(name)
            self._open.discard(name)
            ui.notify(f"Event {name} deleted")
            self._list.refresh()
