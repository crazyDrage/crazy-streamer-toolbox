import json
import re
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.alerts.alert_rule import AlertRule
from streamer_toolbox.core.alerts.alert_store import AlertStore
from streamer_toolbox.core.deck.deck_button import DeckButton
from streamer_toolbox.core.deck.deck_images import DeckImages
from streamer_toolbox.core.deck.deck_page import DeckPage
from streamer_toolbox.core.deck.deck_store import DeckStore
from streamer_toolbox.core.event_types.event_flows import SEND
from streamer_toolbox.core.event_types.event_type import EventType
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.exports.export_finder import FLOW
from streamer_toolbox.core.exports.import_row import BOTH, NEW, REPLACE, SAME, SKIP, TAKEN, ImportRow
from streamer_toolbox.core.exports.toolbox_export import ToolboxExport
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_store import FlowStore
from streamer_toolbox.core.upgrades.settings_version import SETTINGS_VERSION
from streamer_toolbox.core.variables.variable_store import VariableStore
from streamer_toolbox.core.widgets.widget_store import EVENTS, WidgetStore

ORDER = ("event", "variable", "widget", "alert", "flow", "button")  # what a later part may point at comes first
IMPORTED = "Imported"  # the Live page imported buttons go on


class ExportImporter:
    """Brings a `.toolbox` export in (his round 86). rows() is what the import window lists: each part new, the
    same as here, or taken (he picks Replace, Keep both or Skip). needs() is what the export uses but can't
    bring (a box from a plugin, a Twitch reward, an event that isn't in it). run() imports with his choices.

    Keep both gives the part a free name and keeps the export's links right: a flow that runs another flow of
    the export, an alert's or widget's event, a Send box's "Only to". A kept-both flow comes without its
    triggers and a kept-both alert comes switched off, so nothing plays twice. The export's files go into the
    settings folder (media/<export title>/), so the toolbox stays portable; a widget's go into its own folder."""

    def __init__(self, flows: FlowLibrary, alerts: AlertStore, widgets: WidgetStore, events: EventTypeStore,
                 variables: VariableStore, deck: DeckStore, deck_images: DeckImages, actions: ActionRegistry,
                 media: Path, after: Callable[[], Any] = lambda: None) -> None:
        self._flows = flows
        self._alerts = alerts
        self._widgets = widgets
        self._events = events
        self._variables = variables
        self._deck = deck
        self._deck_images = deck_images
        self._actions = actions
        self._media = media
        self._after = after  # the events' flows and shown types once everything is in (EventUsers.start)

    def rows(self, export: ToolboxExport) -> list[ImportRow]:
        if export.settings_version > SETTINGS_VERSION:
            raise ValueError(f"this export was made by a newer toolbox ({export.app_version}): update this "
                             "toolbox first")
        rows = []
        for entry in sorted(export.entries, key=lambda e: ORDER.index(e["kind"]) if e["kind"] in ORDER else 99):
            kind, key, title = entry["kind"], str(entry["key"]), str(entry.get("title") or entry["key"])
            if kind not in ORDER:
                continue
            state = self._state(kind, key, entry, export)
            choices = () if state != TAKEN else (REPLACE, SKIP) if kind == "variable" else (REPLACE, BOTH, SKIP)
            choice = "" if state != TAKEN else SKIP if kind in ("event", "variable") else BOTH
            rows.append(ImportRow(kind, key, title, state, choice, choices))
        return rows

    def needs(self, export: ToolboxExport) -> list[str]:
        """What the export uses that isn't inside it, one line each."""
        inside = {(e["kind"], str(e["key"])) for e in export.entries}
        said: list[str] = []
        for entry in export.entries:
            data = entry.get("data") or {}
            if entry["kind"] == "flow":
                for node in data.get("nodes", []):
                    action = str(node.get("action", ""))
                    known = action in self._actions or action.startswith((FLOW, SEND))
                    if action and not known:
                        said.append(f"The box {action} (a plugin or a connection this toolbox doesn't have)")
                    if action.startswith(FLOW) and ("flow", action.removeprefix(FLOW)) not in inside \
                            and self._flows.get(action.removeprefix(FLOW)) is None:
                        said.append(f"The flow {action.removeprefix(FLOW)} (a box in {entry.get('title')})")
                for trigger in data.get("triggers", []):
                    reward = trigger.get("reward")
                    if reward:
                        said.append(f"The Twitch reward \"{reward}\" (made on Twitch, it can't come along)")
            events = [data.get("event")] if entry["kind"] == "alert" else []
            if entry["kind"] == "widget":
                events = _widget_events(entry, export)
            for event in filter(None, events):
                if ("event", event) not in inside and self._events.get(event) is None:
                    said.append(f"The event {event}")
        return list(dict.fromkeys(said))

    def run(self, export: ToolboxExport, choices: dict[tuple[str, str], str] | None = None) -> list[str]:
        """Imports with his choices (part id → replace / both / skip; a taken part he didn't choose for gets
        the window's first pick). What was done, one line each."""
        rows = self.rows(export)
        picked = {row.id: (choices or {}).get(row.id, row.choice) for row in rows}
        entries = {(e["kind"], str(e["key"])): e for e in export.entries}
        files = self._files(export)
        renamed: dict[str, dict[str, str]] = {kind: {} for kind in ORDER}
        for row in rows:  # every new name first: a flow may run one that comes after it
            if row.state == TAKEN and picked[row.id] == BOTH:
                taken = set(renamed[row.kind].values())
                renamed[row.kind][row.key] = self._free(row.kind, row.key, taken)
        table = {**files, **self._links(renamed)}
        said = []
        for row in rows:
            if row.state == SAME or picked[row.id] == SKIP:
                said.append(f"{row.label}: {'the same as yours' if row.state == SAME else 'skipped'}")
                continue
            both = row.key in renamed[row.kind]
            new_key = renamed[row.kind].get(row.key, row.key)
            data = _swap(entries[row.id].get("data") or {}, table)
            getattr(self, f"_put_{row.kind}")(new_key, data, entries[row.id], export, both, renamed)
            said.append(f"{row.label}: " + (f"kept both, yours stays, this one is {new_key}" if both
                                            else "replaced yours" if row.state == TAKEN else "added"))
        self._after()
        return said

    # ---- what is here ----

    def _state(self, kind: str, key: str, entry: dict[str, Any], export: ToolboxExport) -> str:
        data = entry.get("data") or {}
        if kind == "alert":
            here = self._alerts.get(key)
            return NEW if here is None else SAME if here.to_dict() == AlertRule.from_dict(data).to_dict() else TAKEN
        if kind == "widget":
            here = {place: path.read_bytes() for place, path in self._widgets.own_files(key).items()}
            mine = {name: export.files.get(place) for name, place in (entry.get("files") or {}).items()}
            return NEW if not here else SAME if here == mine else TAKEN
        if kind == "event":
            here = self._events.get(key)
            shown = replace(EventType.from_dict(data), hidden=here.hidden) if here else None
            return NEW if here is None else SAME if here == shown else TAKEN
        if kind == "flow":
            here = self._flows.get(key)
            if here is None:
                return NEW
            same = FlowStore.to_data(here) == FlowStore.to_data(FlowStore.parse(key, data))
            return SAME if same and not entry.get("files") else TAKEN
        if kind == "variable":
            if key not in self._variables.names():
                return NEW
            return SAME if self._variables.get(key) == data.get("value") else TAKEN
        if kind == "button":
            page = self._deck.load().page(str(data.get("page", "")))
            buttons = page.buttons if page else []
            same = any(b.label == data.get("label") and b.action == data.get("action") for b in buttons)
            return SAME if same else NEW
        return NEW

    def _free(self, kind: str, key: str, taken: set[str]) -> str:
        """A name for a kept-both part that nothing here and no other part of this import has."""
        if kind == "flow":
            return self._flows.free_name(key, taken)
        here = {"alert": lambda name: self._alerts.get(name) is not None,
                "widget": lambda name: self._widgets.get(name) is not None,
                "event": lambda name: self._events.get(name) is not None}[kind]
        number = 2
        while here(f"{key}_{number}") or f"{key}_{number}" in taken:
            number += 1
        return f"{key}_{number}"

    # ---- putting it in ----

    def _put_event(self, key: str, data: dict[str, Any], entry, export, both: bool, renamed) -> None:
        self._events.save(key, replace(EventType.from_dict(data), name=key))

    def _put_variable(self, key: str, data: dict[str, Any], entry, export, both: bool, renamed) -> None:
        self._variables.set(key, data.get("value"))

    def _put_widget(self, key: str, data: dict[str, Any], entry, export, both: bool, renamed) -> None:
        files = {name: export.files[place] for name, place in (entry.get("files") or {}).items()
                 if place in export.files}
        events = renamed["event"]
        if EVENTS in files and events:
            listed = json.loads(files[EVENTS].decode("utf-8"))
            files[EVENTS] = json.dumps([events.get(e, e) for e in listed], indent=2).encode("utf-8")
        self._widgets.put_files(key, files)

    def _put_alert(self, key: str, data: dict[str, Any], entry, export, both: bool, renamed) -> None:
        rule = AlertRule.from_dict({**data, "id": key})
        rule = replace(rule, event=renamed["event"].get(rule.event, rule.event))
        if both:
            rule = replace(rule, name=f"{rule.name} (imported)", on=False)
        self._alerts.save(rule)

    def _put_flow(self, key: str, data: dict[str, Any], entry, export, both: bool, renamed) -> None:
        flow = FlowStore.parse(key, data)
        if self._flows.upgrade is not None:
            flow = self._flows.upgrade(flow, export.settings_version)
        if both:
            flow = replace(flow.without_triggers(), label=f"{flow.label} (imported)")
        self._flows.save(replace(flow, name=key))

    def _put_button(self, key: str, data: dict[str, Any], entry, export, both: bool, renamed) -> None:
        button = DeckButton.from_dict(data)
        button.x = button.y = -1  # the first free spot of the page
        flow = button.action.removeprefix(FLOW)
        if button.action.startswith(FLOW) and flow in renamed["flow"]:
            button.action = FLOW + renamed["flow"][flow]
        for name, place in (entry.get("files") or {}).items():
            if name == button.image and place in export.files:
                button.image = self._deck_images.add(name, export.files[place])
        deck = self._deck.load()
        name = str(data.get("page") or IMPORTED)
        page = deck.page(name)
        if page is None:  # its page as it was named where it was made
            page = DeckPage(name)
            deck.pages.append(page)
        page.buttons.append(button)
        page.place()
        self._deck.save(deck)

    # ---- names and files ----

    def _files(self, export: ToolboxExport) -> dict[str, str]:
        """The export's files (not a widget's) into media/<its title>/: path as written in the data → the new
        file's path. The same file again keeps its name, another one with a taken name gets a number."""
        folder = self._media / (re.sub(r"[^A-Za-z0-9_.-]+", "_", export.title).strip("._") or "import")
        swapped = {}
        for entry in export.entries:
            if entry["kind"] in ("widget", "button"):
                continue
            for written, place in (entry.get("files") or {}).items():
                content = export.files.get(place)
                if content is None:
                    continue
                name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(place).name) or "file"
                target, number = folder / name, 2
                while target.is_file() and target.read_bytes() != content:
                    target, number = folder / f"{Path(name).stem}_{number}{Path(name).suffix}", number + 1
                folder.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                swapped[written] = str(target.resolve())
        return swapped

    @staticmethod
    def _links(renamed: dict[str, dict[str, str]]) -> dict[str, str]:
        """Texts in an export's data that name a part that got a new name: a box running a flow, a Send box,
        a Send box's Only to."""
        table = {FLOW + old: FLOW + new for old, new in renamed["flow"].items()}
        table.update({SEND + old: SEND + new for old, new in renamed["event"].items()})
        table.update({f"alert {old}": f"alert {new}" for old, new in renamed["alert"].items()})
        table.update({f"widget {old}": f"widget {new}" for old, new in renamed["widget"].items()})
        return table


def _swap(value: Any, table: dict[str, str]) -> Any:
    """The data with every text that is a key of the table (exactly) changed to its value."""
    if isinstance(value, dict):
        return {k: _swap(v, table) for k, v in value.items()}
    if isinstance(value, list):
        return [_swap(v, table) for v in value]
    if isinstance(value, str):
        return table.get(value, value)
    return value


def _widget_events(entry: dict[str, Any], export: ToolboxExport) -> list[str]:
    place = (entry.get("files") or {}).get(EVENTS)
    try:
        return [str(e) for e in json.loads(export.files[place].decode("utf-8"))] if place in export.files else []
    except ValueError:
        return []
