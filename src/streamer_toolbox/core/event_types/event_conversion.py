import re
from dataclasses import replace

from streamer_toolbox.core.alerts.alert_input import AlertInput
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.event_types.event_flows import ONLY_TO, action_name
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.event_types.event_value import KINDS, EventValue
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.widgets.widget_input import WidgetInput
from streamer_toolbox.core.widgets.widget_store import WidgetStore

WIDGET_SEND, ALERT_PLAY = "widget.send.", "alert.play."  # the boxes flows used before round 78
ALERTS_BEFORE = "alerts.before_round_79.json"
# inputs the usual alerts called otherwise before round 78 → the event's value
RENAMED = {"cheer": {"amount": "bits"}, "raid": {"amount": "viewers"}}


class EventConversion:
    """Once, when a toolbox from before round 78 starts (his answer 2 a: "converted once, old file kept"):
    - a widget's inputs (inputs.json, round 74) become the event types it gets: a chat / follow / ... input the
      event of that name (its own listener one more name of it), a custom input an event type of its own;
    - an alert without an event gets the usual one of its name when its inputs fit (cheer's amount is called
      bits there), else an event type of its own from its inputs; alerts.json is kept as it was first;
    - a flow's box for a widget's input or an alert becomes that event's Send box with "Only to" that widget or
      alert, so it reaches exactly what it reached before (and the event's own flow isn't made on top). The
      alerts' own boxes are gone (his answer 2 b): one found in a flow later is changed the same way
      (leftovers(), every start, and flow() for an imported one: EventsUpgrade).
    inputs.json stays next to the widget, as it was."""

    def __init__(self, events: EventTypeStore, widgets: WidgetStore, alerts: AlertStore, flows: FlowLibrary) -> None:
        self._events = events
        self._widgets = widgets
        self._alerts = alerts
        self._flows = flows

    def run(self) -> list[str]:
        """What it converted, one line each (for the log)."""
        said: list[str] = []
        boxes = self._widget_inputs(said)
        boxes.update(self._alert_events(said))
        self._flow_boxes({**self._boxes(), **boxes}, said)
        return said

    def leftovers(self) -> list[str]:
        """Every flow with a box from before round 78 that is still there (a file copied in by hand) sends the
        event now; one line per flow."""
        said: list[str] = []
        self._flow_boxes(self._boxes(), said)
        return said

    def flow(self, flow: Flow) -> Flow:
        """One flow (an imported one) with its boxes from before round 78 sending events, as run() changes the
        saved ones. A box of a widget or alert this toolbox doesn't have stays as it is."""
        return self._converted(flow, self._boxes())

    def _boxes(self) -> dict[str, tuple[str, str, dict[str, str]]]:
        """The old boxes this toolbox can still tell the event of, without making a new event type."""
        boxes = {f"{ALERT_PLAY}{rule.id}": (rule.event, f"alert {rule.id}", {})
                 for rule in self._alerts.all() if rule.event}
        for name in self._widgets.names():
            widget = self._widgets.get(name)
            for item in (widget.inputs or ()) if widget is not None else ():
                kind = self._events.get(item.name if item.kind == "custom" else item.kind)
                if kind is not None:
                    boxes[f"{WIDGET_SEND}{name}.{item.name}"] = (kind.name, f"widget {name}", {})
        return boxes

    def _widget_inputs(self, said: list[str]) -> dict[str, tuple[str, str, dict[str, str]]]:
        boxes = {}
        for name in self._widgets.names():
            widget = self._widgets.get(name)
            if widget is None or widget.events is not None or widget.inputs is None:
                continue
            events = []
            for item in widget.inputs:
                event = self._event_for(item)
                events.append(event)
                boxes[f"{WIDGET_SEND}{name}.{item.name}"] = (event, f"widget {name}", {})
            self._widgets.save(replace(widget, events=tuple(dict.fromkeys(events))))
            said.append(f"widget {name}: inputs → events {', '.join(events) or 'none'}")
        return boxes

    def _event_for(self, item: WidgetInput) -> str:
        kind = self._events.get(item.kind) if item.kind != "custom" else None
        if kind is None:
            values = tuple(EventValue(field) for field in item.field_names)
            same = self._events.get(item.name)
            if same is not None and [v.name for v in same.values] == list(item.field_names):
                return same.name
            other = (item.heard_as,) if item.heard_as != item.name else ()
            return self._events.add(item.name, values, other).name
        if item.listener.strip() and not kind.known_as(item.listener.strip()):
            self._events.save(kind.name, replace(kind, also_known_as=(*kind.also_known_as, item.listener.strip())))
        return kind.name

    def _alert_events(self, said: list[str]) -> dict[str, tuple[str, str, dict[str, str]]]:
        boxes = {}
        rules = [rule for rule in self._alerts.all() if not rule.event]
        if rules:
            self._alerts.keep_copy(ALERTS_BEFORE)
        for rule in rules:
            usual = self._events.get(re.sub(r"_\d+$", "", rule.id))
            renamed = RENAMED.get(usual.name, {}) if usual else {}
            names = [renamed.get(i.name, i.name) for i in rule.inputs]
            if usual is not None and usual.default and all(usual.value(n) is not None for n in names):
                event, changed = usual.name, rule
                for old, new in renamed.items():
                    if rule.input(old) is not None:
                        changed = changed.renamed_input(old, new)
            else:
                event, changed, renamed = self._own_event(rule.id, rule.inputs), rule, {}
            self._alerts.save(replace(changed, event=event))
            boxes[f"{ALERT_PLAY}{rule.id}"] = (event, f"alert {rule.id}", renamed)
            said.append(f"alert {rule.title}: plays on the event {event}")
        return boxes

    def _own_event(self, name: str, inputs: tuple[AlertInput, ...]) -> str:
        values = tuple(EventValue(i.name, i.example, i.kind if i.kind in KINDS else "text") for i in inputs)
        return self._events.add(name, values).name

    def _flow_boxes(self, boxes: dict[str, tuple[str, str, dict[str, str]]], said: list[str]) -> None:
        if not boxes:
            return
        for flow in self._flows.all():
            changed = self._converted(flow, boxes)
            if changed != flow:
                self._flows.save(changed, flow.name)
                said.append(f"flow {flow.label}: sends events now")

    def _converted(self, flow: Flow, boxes: dict[str, tuple[str, str, dict[str, str]]]) -> Flow:
        if not any(node.action in boxes for node in flow.nodes):
            return flow
        nodes = []
        for node in flow.nodes:
            if node.action in boxes:
                event, only_to, renamed = boxes[node.action]
                params = {renamed.get(key, key): value for key, value in node.params.items()}
                node = replace(node, action=action_name(event), params={**params, ONLY_TO: only_to})
                self._events.mark_flow_made(event)  # it is sent already: no flow of its own on top
            nodes.append(node)
        return replace(flow, nodes=tuple(nodes))
