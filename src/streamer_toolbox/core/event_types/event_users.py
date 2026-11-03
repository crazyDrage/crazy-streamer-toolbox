import re
from dataclasses import replace

from streamer_toolbox.core.alerts.alert_input import AlertInput
from streamer_toolbox.core.alerts.alert_rule import AlertRule, default_parts
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.event_types.event_flows import EventFlows
from streamer_toolbox.core.event_types.event_type import EventType
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_value import check_value_name
from streamer_toolbox.core.widgets.widget_store import WidgetStore

# a value's kind → the kind of the alert input it becomes (an alert shows a colour or yes / no as text)
ALERT_KINDS = {"text": "text", "number": "number", "colour": "text", "yes_no": "text", "picture": "picture",
               "sound": "sound"}


class EventUsers:
    """Who uses which event type (his round 78): the widgets that get it (their events.json) and the alerts that
    play on it. Picking an event brings it out of hiding and makes its own flow once (EventFlows). An alert's
    inputs are its event's values, kept in step here (follow_events); renaming an event or a value is done here
    too, so the widgets, alerts and flows that use it follow."""

    def __init__(self, events: EventTypeStore, widgets: WidgetStore, alerts: AlertStore, flows: EventFlows) -> None:
        self._events = events
        self._widgets = widgets
        self._alerts = alerts
        self._flows = flows

    # ---- who uses it ----

    def widgets_of(self, event: str) -> list[str]:
        return [name for name in self._widgets.names() if event in self.events_of(name)]

    def events_of(self, widget: str) -> tuple[str, ...]:
        """The event types that widget gets."""
        found = self._widgets.get(widget)
        return (found.events or ()) if found else ()

    def in_code(self, widget: str) -> tuple[str, ...]:
        """The event types that widget's code listens for (from_code)."""
        found = self._widgets.get(widget)
        return self.from_code(found.js) if found else ()

    def alerts_of(self, event: str) -> list[AlertRule]:
        return [rule for rule in self._alerts.all() if rule.event == event]

    def users(self, event: str) -> list[str]:
        """'Widget chat_box', 'Alert Follow', ...: what the Events tab says under "Used by"."""
        return [f"Widget {name}" for name in self.widgets_of(event)] + \
            [f"Alert {rule.title}" for rule in self.alerts_of(event)]

    def choices(self, event: str) -> dict[str, str]:
        """What a Send box's "Only to" offers: each widget and alert that uses the event."""
        return {**{f"widget {name}": f"Widget {name}" for name in self.widgets_of(event)},
                **{f"alert {rule.id}": f"Alert {rule.title}" for rule in self.alerts_of(event)}}

    def unreached(self, event: str) -> list[str]:
        """The users no flow sends the event to (only flows with "Only to" someone else send it)."""
        sent = [only_to for _, only_to in self._flows.sending(event)]
        if "" in sent:
            return []
        return [title for key, title in self.choices(event).items() if key not in sent]

    # ---- picking ----

    def set_widget_events(self, widget: str, events: tuple[str, ...]) -> list[str]:
        """The widget gets these event types; the flows made for them (their names)."""
        found = self._widgets.get(widget)
        if found is None:
            return []
        self._widgets.save(replace(found, events=tuple(dict.fromkeys(events))))
        return self._used(events)

    def give_events(self, widget: str) -> list[str]:
        """A widget whose events were never set (made new, imported, or from before round 78 without inputs) gets
        the ones its code listens for (from_code). The flows made for them."""
        found = self._widgets.get(widget)
        if found is None or found.events is not None:
            return []
        return self.set_widget_events(widget, self.from_code(found.js))

    def from_code(self, js: str) -> tuple[str, ...]:
        """The event types a widget's code listens for: each one whose other name (or own) it names in quotes
        ('message', "follower-latest", ...: subscriber-latest is sub, resub and gift)."""
        found = []
        for kind in self._events.all():
            if any(re.search(rf"""['"`]{re.escape(name)}['"`]""", js) for name in kind.also_known_as):
                found.append(kind.name)
        return tuple(found)

    def set_alert_event(self, alert_id: str, event: str) -> list[str]:
        """The alert plays on this event type now; its inputs become the event's values. The flows made."""
        rule = self._alerts.get(alert_id)
        kind = self._events.get(event)
        if rule is None or kind is None:
            return []
        self._alerts.save(inputs_from(replace(rule, event=event), kind))
        return self._used((event,))

    def new_alert(self, name: str, event: str, text: str = "") -> tuple[AlertRule, list[str]]:
        """A new alert (off) on that event type, with its values as inputs; the flows made."""
        rule = self._alerts.add(name, text=text, event=event)
        made = self.set_alert_event(rule.id, event)
        rule = self._alerts.get(rule.id)
        number = next((i.name for i in rule.inputs if i.kind == "number"), "")
        if number:  # its first number is the amount ("only from" and the bigger alerts go by it)
            rule = rule.with_inputs(tuple(replace(i, amount=i.name == number) for i in rule.inputs))
        text = "{user}" if rule.input("user") else ""
        rule = replace(rule, text=rule.text or text, parts=default_parts(rule.inputs))
        self._alerts.save(rule)
        return rule, made

    def _used(self, events: tuple[str, ...]) -> list[str]:
        made = []
        for event in events:
            self._events.show(event)
            name = self._flows.make_once(event)
            if name:
                made.append(name)
        return made

    # ---- keeping in step ----

    def follow_events(self) -> None:
        """Every alert's inputs as its event's values are now (an alert whose event is gone keeps its own)."""
        for rule in self._alerts.all():
            kind = self._events.get(rule.event)
            if kind is not None:
                changed = inputs_from(rule, kind)
                if changed != rule:
                    self._alerts.save(changed)

    def start(self) -> list[str]:
        """At start: the alerts follow their events, each used event is out of hiding and has its flow (made
        once). A toolbox that just got its first alerts hides the folder Events, as it hid Alerts. The flows made."""
        self.follow_events()
        first = bool(self._alerts.unstarted)
        used = [rule.event for rule in self._alerts.all() if rule.event] + \
            [event for name in self._widgets.names() for event in self.events_of(name)]
        made = self._used(tuple(dict.fromkeys(used)))
        if first:
            if made:
                self._flows.hide_folder()
            self._alerts.started()
        return made

    def rename_event(self, old: str, new: str) -> None:
        """The event type gets another name; widgets, alerts and flows that use it follow. ValueError: a name
        that is taken or not allowed."""
        kind = self._events.get(old)
        if kind is None:
            return
        self._events.save(old, replace(kind, name=new))
        for name in self.widgets_of(old):
            widget = self._widgets.get(name)
            self._widgets.save(replace(widget, events=tuple(new if e == old else e for e in widget.events)))
        for rule in self.alerts_of(old):
            self._alerts.save(replace(rule, event=new))
        self._flows.renamed_event(old, new)

    def rename_value(self, event: str, old: str, new: str) -> None:
        """A value of the event type gets another name; {old} in its alerts' words says {new}, its Send boxes
        have the new field."""
        kind = self._events.get(event)
        if kind is None or kind.value(old) is None:
            return
        check_value_name(new)
        if kind.value(new) is not None:
            raise ValueError(f"{event} has a value {new!r} already")
        for rule in self.alerts_of(event):  # first: the event's change makes the alerts follow it by name
            self._alerts.save(rule.renamed_input(old, new))
        self._events.save(event, replace(kind, values=tuple(replace(v, name=new) if v.name == old else v
                                                            for v in kind.values)))
        self._flows.renamed_value(event, old, new)


def inputs_from(rule: AlertRule, kind: EventType) -> AlertRule:
    """The alert with the event's values as its inputs; each keeps its example and amount tick by name (a new
    one's example is the value's default)."""
    inputs = []
    for value in kind.values:
        had = rule.input(value.name)
        inputs.append(AlertInput(value.name, ALERT_KINDS[value.kind], had.example if had else value.default,
                                 had.amount if had else False))
    return replace(rule, inputs=tuple(inputs))
