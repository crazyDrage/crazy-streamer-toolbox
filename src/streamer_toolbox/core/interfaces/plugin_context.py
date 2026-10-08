from abc import ABC, abstractmethod
from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter

from streamer_toolbox.core.actions.json_boxes import Send
from streamer_toolbox.core.actions.registered_action import ActionHandler, OptionsProvider
from streamer_toolbox.core.events.event_bus import EventHandler
from streamer_toolbox.core.interfaces.connection import Connection
from streamer_toolbox.core.values.value_kind import ValueKind


class PluginContext(ABC):
    """The only door a plugin gets into the toolbox, so the internals can change behind it."""

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        ...

    @abstractmethod
    def add_action(self, name: str, handler: ActionHandler, description: str = "", label: str = "",
                   **box: Any) -> None:
        """Register an action as "<plugin_id>.<name>" (runnable from SAMMI, Kit and the GUI).

        label is the button text on the Live page (default: the name, humanised); description shows under it.
        **box is what a box in the flow editor can have besides its fields, the same keywords as
        ActionRegistry.add: group, options (pickers), outputs, hints, labels, files, ports, live, flow_only, ...
        """

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
