import json
import re
from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.deck.deck_images import DeckImages
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.event_types.event_flows import SEND
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.exports.export_part import KINDS, ExportPart
from streamer_toolbox.core.exports.toolbox_export import ToolboxExport
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.widgets.widget_store import WidgetStore

FLOW = "flow."  # a box that runs another flow: flow.<its file name>
VARIABLE = re.compile(r"\$\{var\.([A-Za-z0-9_]+)")


class ExportFinder:
    """What goes into an export (his round 86: "whole flow/alert/widget with everything connected"). From what
    he picks, it follows the links the toolbox knows:
    - an alert → its event (its files: picture, sound, picture pieces, the bigger alerts' files);
    - a widget → its events (its whole folder without data/);
    - an event → the flows that send it; other alerts and widgets on it are offered, not ticked;
    - a flow → the flows it runs as boxes, the events it sends, the global variables it uses, the files its
      boxes name (a sound's path); the Live buttons that run it are offered, not ticked.
    What is only offered isn't followed further until he ticks it (connected(..., ticked=...))."""

    def __init__(self, flows: FlowLibrary, alerts: AlertStore, widgets: WidgetStore, events: EventTypeStore,
                 variables: VariableStore, deck: DeckStore, deck_images: DeckImages, actions: ActionRegistry) -> None:
        self._flows = flows
        self._alerts = alerts
        self._widgets = widgets
        self._events = events
        self._variables = variables
        self._deck = deck
        self._deck_images = deck_images
        self._actions = actions

    def choices(self) -> dict[str, list[tuple[str, str]]]:
        """What he can start an export from, per kind: (key, title), A-Z."""
        def sort(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
            return sorted(items, key=lambda item: item[1].casefold())
        return {"alert": sort([(r.id, r.title) for r in self._alerts.all()]),
                "widget": sort([(n, n) for n in self._widgets.names()]),
                "event": sort([(t.name, t.name) for t in self._events.all() if not t.hidden]),
                "flow": sort([(f.name, f.label) for f in self._flows.all()])}

    def connected(self, picked: list[tuple[str, str]], ticked: set[tuple[str, str]] = frozenset(),
                  unticked: set[tuple[str, str]] = frozenset()) -> list[ExportPart]:
        """Everything connected to what he picked, in the order found (what he picked first). `ticked`: offered
        parts he ticked (followed too); `unticked`: parts he took out (listed, not followed)."""
        found: dict[tuple[str, str], ExportPart] = {}
        waiting = [ExportPart(kind, key, self._title(kind, key), "you picked it") for kind, key in picked]
        while waiting:
            part = waiting.pop(0)
            if part.id in found or not self._title(*part.id):
                continue
            ticks = (part.ticked or part.id in ticked) and part.id not in unticked
            part = ExportPart(part.kind, part.key, part.title, part.why, ticks)
            found[part.id] = part
            if ticks:
                waiting += [p for p in self._links(part) if p.id not in found]
        return list(found.values())

    def export(self, title: str, parts: list[ExportPart]) -> ToolboxExport:
        """The ticked parts as one export file."""
        made = ToolboxExport(title)
        for part in (p for p in parts if p.ticked):
            data, files = self._data(part)
            places = {}
            for name, path in files.items():
                place = (f"widgets/{part.key}/{name}" if part.kind == "widget"
                         else f"files/{len(made.files) + 1}/{Path(path).name}")
                made.files[place] = (_typed_values(Path(path), files.get("fields.json"))
                                     if part.kind == "widget" and name == "values.json" else Path(path).read_bytes())
                places[name] = place
            made.entries.append({"kind": part.kind, "key": part.key, "title": part.title, "data": data,
                                 "files": places})
        return made

    def files_of(self, part: ExportPart) -> dict[str, Path]:
        """The files that go along with a part: name in its data (or place in a widget's folder) → file."""
        return self._data(part)[1]

    # ---- the links ----

    def _links(self, part: ExportPart) -> list[ExportPart]:
        kind, key = part.id
        if kind == "alert":
            rule = self._alerts.get(key)
            return [self._part("event", rule.event, f"{rule.title} plays on it")] if rule.event else []
        if kind == "widget":
            widget = self._widgets.get(key)
            return [self._part("event", e, f"widget {key} gets it") for e in (widget.events or ())]
        if kind == "event":
            senders = [self._part("flow", f.name, f"sends the event {key}") for f in self._flows.all()
                       if any(n.action == SEND + key for n in f.nodes)]
            users = [self._part("alert", r.id, f"also plays on {key}", False) for r in self._alerts.all()
                     if r.event == key]
            users += [self._part("widget", n, f"also gets {key}", False) for n in self._widgets.names()
                      if key in (self._widgets.get(n).events or ())]
            return senders + users
        if kind == "flow":
            flow = self._flows.get(key)
            return self._flow_links(flow)
        return []

    def _flow_links(self, flow: Flow) -> list[ExportPart]:
        links = []
        for node in flow.nodes:
            if node.action.startswith(FLOW) and self._flows.get(node.action.removeprefix(FLOW)):
                links.append(self._part("flow", node.action.removeprefix(FLOW), f"a box in {flow.label}"))
            elif node.action.startswith(SEND):
                links.append(self._part("event", node.action.removeprefix(SEND), f"{flow.label} sends it"))
        for name in self.variables_of(flow):
            links.append(self._part("variable", name, f"{flow.label} uses it"))
        for page in self._deck.load().pages:
            for number, button in enumerate(page.buttons):
                if button.action == flow.action_name:
                    links.append(self._part("button", f"{page.name}/{number}", f"starts {flow.label}", False))
        return links

    def variables_of(self, flow: Flow) -> list[str]:
        """The global variables (that exist) a flow's boxes read or write."""
        names: list[str] = []
        for node in flow.nodes:
            fields = self._actions.get(node.action).variable_fields if node.action in self._actions else ()
            names += [str(v) for k, v in node.params.items() if k in fields and isinstance(v, str)]
            names += VARIABLE.findall(str(node.params))
            if node.save_as:
                names.append(node.save_as)
        known = set(self._variables.names())
        return [n for n in dict.fromkeys(names) if n in known]

    def _part(self, kind: str, key: str, why: str, ticked: bool = True) -> ExportPart:
        return ExportPart(kind, key, self._title(kind, key) or key, why, ticked)

    def _title(self, kind: str, key: str) -> str:
        """Its name in the lists; "" when there is no such thing (any more)."""
        if kind == "alert":
            rule = self._alerts.get(key)
            return rule.title if rule else ""
        if kind == "widget":
            return key if self._widgets.get(key) is not None else ""
        if kind == "event":
            return key if self._events.get(key) is not None else ""
        if kind == "flow":
            flow = self._flows.get(key)
            return flow.label if flow else ""
        if kind == "variable":
            return key if key in self._variables.names() else ""
        if kind == "button":
            button = self._button(key)
            return button[1].label if button else ""
        return ""

    def _button(self, key: str) -> tuple[str, Any] | None:
        page_name, _, number = key.rpartition("/")
        page = self._deck.load().page(page_name)
        if page is None or not number.isdigit() or int(number) >= len(page.buttons):
            return None
        return page.name, page.buttons[int(number)]

    # ---- what is kept ----

    def _data(self, part: ExportPart) -> tuple[dict[str, Any], dict[str, Path]]:
        kind, key = part.id
        if kind == "alert":
            data = self._alerts.get(key).to_dict()
            return data, _files_in(data)
        if kind == "widget":
            return {}, self._widgets.own_files(key)
        if kind == "event":
            return self._events.get(key).to_dict(), {}
        if kind == "flow":
            data = {"name": key, **FlowStore.to_data(self._flows.get(key))}
            return data, _files_in(data)
        if kind == "variable":
            return {"value": self._variables.get(key)}, {}
        if kind == "button":
            page, button = self._button(key)
            data = {"page": page, **button.to_dict()}
            image = self._deck_images.folder / button.image if button.image else None
            return data, ({button.image: image} if image is not None and image.is_file() else {})
        raise ValueError(f"not something to export: {KINDS.get(kind, kind)}")


def _files_in(value: Any) -> dict[str, Path]:
    """The files a part's data names by their full path (an alert's picture, a sound box's file) that are on this
    PC: path as written → file."""
    found: dict[str, Path] = {}
    if isinstance(value, dict):
        for inner in value.values():
            found.update(_files_in(inner))
    elif isinstance(value, list):
        for inner in value:
            found.update(_files_in(inner))
    elif isinstance(value, str) and 3 < len(value) < 500 and "\n" not in value:
        path = Path(value.strip('"'))
        try:
            if path.is_absolute() and path.is_file():
                found[value] = path
        except OSError:
            pass
    return found


def _typed_values(values: Path, fields: Path | None) -> bytes:
    """A widget's values.json with only the values that have a field (his round 87): StreamElements leaves
    values like an account token there that no field shows and the widget doesn't use."""
    try:
        typed = json.loads(values.read_text(encoding="utf-8"))
        names = json.loads(fields.read_text(encoding="utf-8")) if fields is not None else None
    except (OSError, ValueError):
        return values.read_bytes()
    if not isinstance(typed, dict) or not isinstance(names, dict):
        return values.read_bytes()
    return json.dumps({k: v for k, v in typed.items() if k in names}, indent=2).encode("utf-8")
