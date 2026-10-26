from abc import ABC, abstractmethod
from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter

from streamer_toolbox.core.actions.json_boxes import Send
from streamer_toolbox.core.actions.registered_action import ActionHandler, OptionsProvider
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.events.event_bus import EventHandler
from streamer_toolbox.core.flows.box_signals import BoxSignals
from streamer_toolbox.core.flows.retrigger import Retrigger
from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.interfaces.connection import Connection
from streamer_toolbox.core.interfaces.field_editor import FieldEditor
from streamer_toolbox.core.interfaces.listener import Listener
from streamer_toolbox.core.interfaces.page import Page
from streamer_toolbox.core.interfaces.panel import Panel
from streamer_toolbox.core.interfaces.tool import Tool
from streamer_toolbox.core.interfaces.trigger import Trigger
from streamer_toolbox.core.values.value_kind import ValueKind


Addable = Box | Trigger | Connection | Tool | Page | Panel | Listener | APIRouter | type[FieldEditor]


class PluginContext(ABC):
    """The only door a plugin gets into the toolbox, so the internals can change behind it.

    What a plugin adds goes through add(): one class per kind of thing (core/interfaces: Box, Trigger,
    Connection, Tool, Page, Panel, Listener, FieldEditor; FastAPI's own APIRouter for routes). The rest of the
    methods are what a plugin can use (run_action, settings, ask_yes_no, ...). The add_* methods are the
    older way of api_version 1 to 3 and stay for those plugins."""

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        ...

    def add(self, thing: Addable) -> str:
        """Adds one thing to the toolbox, whatever kind it is. Returns its full name where it has one: a box's
        "<id>.<name>", a trigger's "<id>.<event>", a field editor's "<id>.<kind>", a page's path; else ""."""
        if isinstance(thing, Box):
            if not thing.name:
                raise ValueError(f"{type(thing).__name__} needs a name")
            self.add_action(thing.name, thing.run, thing.help, thing.label, **thing.box_options())
            return f"{self.plugin_id}.{thing.name}"
        if isinstance(thing, Trigger):
            if not (thing.event and thing.title):
                raise ValueError(f"{type(thing).__name__} needs an event and a title")
            name = self.add_trigger(thing.event, thing.title, thing.fields, thing.icon, thing.pick, thing.example,
                                    thing.description, thing.choices)
            thing.added(self.publish)
            return name
        if isinstance(thing, Connection):
            self.add_connection(thing)
            return thing.id
        if isinstance(thing, Tool):
            self.add_tool(thing.title, thing.build, thing.icon, thing.description)
            return ""
        if isinstance(thing, Page):
            return self.add_page(thing.title, thing.build, thing.subpath, thing.icon)
        if isinstance(thing, Panel):
            self.add_panel(thing.title, thing.build, thing.section)
            return ""
        if isinstance(thing, Listener):
            self.on_event(thing.heard)
            return ""
        if isinstance(thing, APIRouter):
            self.add_router(thing)
            return ""
        if isinstance(thing, type) and issubclass(thing, FieldEditor):
            if not thing.kind:
                raise ValueError(f"{thing.__name__} needs a kind")
            return self.add_field_editor(thing.kind, thing)
        raise TypeError(f"ctx.add takes a Box, Trigger, Connection, Tool, Page, Panel, Listener, APIRouter or a "
                        f"FieldEditor class, not {type(thing).__name__}")

    @abstractmethod
    def secret(self, name: str, label: str, hint: str = "") -> SecretFile:
        """A key, token or password the plugin needs. The streamer types it into a field on the plugin's card
        under Plugins (it is never shown again); it is kept in config/secrets/<plugin_id>_<name>.txt, encrypted
        while a login is set. `.read()` gives it, or raises with words that say where to type it;
        `.hide(text)` takes it out of a text before it is shown or logged. Asking twice gives the same one."""

    @abstractmethod
    def add_web_boxes(self, folder: Path) -> None:
        """The boxes written as web JSON in `folder` (every *.json file: a web address to call, its inputs and
        outputs; WebBoxes), as "<plugin_id>.<name>". A plugin with only a boxes/ folder and no main.py gets
        this by itself."""

    @abstractmethod
    def add_action(self, name: str, handler: ActionHandler, description: str = "", label: str = "",
                   **box: Any) -> None:
        """Register an action as "<plugin_id>.<name>" (runnable from SAMMI, Kit and the GUI).

        label is the button text on the Live page (default: the name, humanised); description shows under it.
        **box is what a box in the flow editor can have besides its fields: every keyword of ActionRegistry.add
        (group, options, outputs, ports, entries, toggles, port_fields, entry_fields, value_lines, named_lines,
        data_only, join, ends_flow, gives_back, once_per_flow, retrigger, variable_fields, editors, ...; all of
        them in docs/ai/code/action.md). The toolbox's own boxes use nothing a plugin can't: a Loop, an End or a
        Wait can be made the same way (tests/test_plugin_parity.py).
        """

    @abstractmethod
    def box_signals(self) -> Optional[BoxSignals]:
        """Inside a box's handler while it runs in a flow: what arrived at its extra run dots (`entries`, e.g.
        a "stop": has("stop"), await wait_for(seconds, "stop")). None outside a flow (Test box, API)."""

    @abstractmethod
    def retrigger(self) -> Optional[Retrigger]:
        """Inside a box's handler with `retrigger`: the run's Retrigger, so a new start of the flow stretches
        the box's wait (await retrigger.wait(seconds, mode)) instead of running again. None when the flow
        has no switched-on box asking for it."""

    @abstractmethod
    def add_field_editor(self, kind: str, editor: type[FieldEditor]) -> str:
        """A field kind with its own window (a FieldEditor class); returns its full name "<plugin_id>.<kind>",
        which a box names in editors={field: name}."""

    @abstractmethod
    def add_json_boxes(self, folder: Path, send: Send, kinds: Collection[ValueKind] = ()) -> None:
        """Register the boxes written as JSON in `folder` (every *.json file, see JsonBoxes for what a file
        holds) as "<plugin_id>.<name>": each is one request with fields, no Python needed. Running a box calls
        send(request, data). `kinds` are the plugin's own value kinds its fields may name next to the global
        ones (text, number, yes_no, color, file, list, ...), e.g. a picker that asks its program."""

    @abstractmethod
    def add_connection(self, connection: Connection) -> None:
        """Add a program the toolbox talks to: a tab under Connections with its settings and on / off switch,
        started with the toolbox, its boxes hidden while it is off. One per plugin, and its `id` must be the
        plugin's id (its settings are the [<id>] table of toolbox.toml; its boxes are named <id>.<what>)."""

    @abstractmethod
    def add_trigger(self, event: str, title: str, fields: tuple[str, ...], icon: str = "bolt", pick: str = "",
                    example: str = "*", description: str = "",
                    choices: OptionsProvider | Collection[str] | None = None) -> str:
        """Make the event "<plugin_id>.<event>" something a flow can start on. `title` is the trigger's name
        in the Start box, `fields` the keys its data always has (dots to wire from), `pick` the field a
        trigger is matched on (default: the first) and `example` what that input starts with.
        `description` is its one line in the Add trigger window. `choices` makes that input a dropdown
        (typing still works): a list of values, or an async function that returns one, asked each time
        the trigger is shown, so it can ask the running program what it has right now. Returns the event's
        full name."""

    @abstractmethod
    def publish(self, event: str, data: dict[str, Any]) -> None:
        """Tell the toolbox that "<plugin_id>.<event>" happened: flows with that trigger start."""

    @abstractmethod
    def on_event(self, handler: EventHandler) -> None:
        """Hear everything that happens in the toolbox: handler(kind, data) is awaited for every event (a
        follow, a redeem, a timer tick, another plugin's event). Keep it quick and never log what it carries."""

    @abstractmethod
    def add_router(self, router: APIRouter) -> None:
        """Mount the plugin's own API routes under /api/plugins/<plugin_id>."""

    @abstractmethod
    def add_page(self, title: str, builder: Callable[[], None], subpath: str = "", icon: str = "extension") -> str:
        """Add a GUI page at /plugins/<plugin_id>[/subpath]. The main page gets its own entry in the menu,
        under the plugin area, with a Material icon name. Returns its path."""

    @abstractmethod
    def add_panel(self, title: str, builder: Callable[[], None], section: str = "live") -> None:
        """Add a card to a core area: "live" (next to the actions), "connections" or "settings"."""

    @abstractmethod
    def add_static(self, folder: Path) -> str:
        """Serve a folder (JS, CSS, images). Returns its URL prefix."""

    @abstractmethod
    async def ask_yes_no(self, question: str, timeout: float = 20.0) -> Optional[bool]:
        """Ask the streamer in the GUI. None if nobody answered in time."""

    @abstractmethod
    def add_tool(self, title: str, builder: Callable[[], None], icon: str = "build", description: str = "") -> None:
        """Add a tool to the Tools page (e.g. a deck of buttons): a card on its overview, an item under Tools in
        the side menu and a page of its own; builder draws it with NiceGUI each time it opens."""

    @abstractmethod
    async def run_action(self, name: str, **params: Any) -> Any:
        """Run any toolbox action by name, e.g. "sammi.trigger_button" or "flow.desktop"; fails like the action."""

    @abstractmethod
    def has_action(self, name: str) -> bool:
        """Whether an action exists now (e.g. "sammi.get_decks" only while the SAMMI connection is loaded)."""

    @property
    @abstractmethod
    def resources(self) -> Optional[Path]:
        """The plugin's resources/ folder (pictures, default settings, JS), None for an installed plugin."""

    @abstractmethod
    def resource_url(self, name: str) -> str:
        """The URL of a file in resources/, for an image or a script in the GUI."""

    @abstractmethod
    def settings(self) -> dict[str, Any]:
        """The plugin's settings: resources/settings.json with what the streamer saved on top."""

    @abstractmethod
    def save_settings(self, values: dict[str, Any]) -> None:
        """Keep changed settings (in config/plugins/<id>.json, so a plugin update doesn't lose them)."""
