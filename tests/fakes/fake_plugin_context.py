from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.registered_action import ActionHandler, OptionsProvider
from streamer_toolbox.core.events.event_bus import EventHandler
from streamer_toolbox.core.interfaces.connection import Connection
from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.core.actions.json_boxes import JsonBoxes, Send
from streamer_toolbox.core.values.value_kind import ValueKind
from streamer_toolbox.core.values.value_kinds import ValueKinds


class FakePluginContext(PluginContext):
    """Records what a plugin registers; answers yes/no questions with a preset answer. What the plugin
    publishes is kept in `published`; tell() hands an event to the listeners it added."""

    def __init__(self, plugin_id: str, actions: ActionRegistry, answer: Optional[bool] = True,
                 folder: Optional[Path] = None) -> None:
        self._id = plugin_id
        self.actions = actions
        self.folder = folder
        self.tools: list[tuple[str, Callable[[], None]]] = []
        self.saved: dict[str, Any] = {}
        self.answer = answer
        self.routers: list[APIRouter] = []
        self.pages: list[str] = []
        self.panels: list[str] = []
        self.static: list[Path] = []
        self.questions: list[str] = []
        self.connections: list[Connection] = []
        self.triggers: dict[str, tuple[str, tuple[str, ...]]] = {}  # kind → (title, fields)
        self.trigger_choices: dict[str, OptionsProvider | Collection[str]] = {}
        self.published: list[tuple[str, dict[str, Any]]] = []
        self.listeners: list[EventHandler] = []

    @property
    def plugin_id(self) -> str:
        return self._id

    def add_action(self, name: str, handler: ActionHandler, description: str = "", label: str = "",
                   **box: Any) -> None:
        self.actions.add(f"{self._id}.{name}", handler, description, label, **box)

    def add_json_boxes(self, folder: Path, send: Send, kinds: Collection[ValueKind] = ()) -> None:
        JsonBoxes(folder, ValueKinds(kinds)).add_to(self.actions, self._id, send)

    def add_connection(self, connection: Connection) -> None:
        self.connections.append(connection)

    def add_trigger(self, event: str, title: str, fields: tuple[str, ...], icon: str = "bolt", pick: str = "",
                    example: str = "*", description: str = "",
                    choices: OptionsProvider | Collection[str] | None = None) -> str:
        self.triggers[f"{self._id}.{event}"] = (title, tuple(fields))
        if choices is not None:
            self.trigger_choices[f"{self._id}.{event}"] = choices
        return f"{self._id}.{event}"

    def publish(self, event: str, data: dict[str, Any]) -> None:
        self.published.append((f"{self._id}.{event}", dict(data)))

    def on_event(self, handler: EventHandler) -> None:
        self.listeners.append(handler)

    async def tell(self, kind: str, data: dict[str, Any]) -> None:
        """Hands an event to the plugin's listeners, as the toolbox's event bus would."""
        for listener in self.listeners:
            await listener(kind, data)

    def add_router(self, router: APIRouter) -> None:
        self.routers.append(router)

    def add_page(self, title: str, builder: Callable[[], None], subpath: str = "", icon: str = "extension") -> str:
        path = f"/plugins/{self._id}" + (f"/{subpath}" if subpath else "")
        self.pages.append(path)
        return path

    def add_panel(self, title: str, builder: Callable[[], None], section: str = "live") -> None:
        self.panels.append(title)

    def add_static(self, folder: Path) -> str:
        self.static.append(folder)
        return f"/plugin-static/{self._id}"

    async def ask_yes_no(self, question: str, timeout: float = 20.0) -> Optional[bool]:
        self.questions.append(question)
        return self.answer

    def add_tool(self, title: str, builder: Callable[[], None], icon: str = "build", description: str = "") -> None:
        self.tools.append((title, builder))

    async def run_action(self, name: str, **params: Any) -> Any:
        return await self.actions.run(name, **params)

    def has_action(self, name: str) -> bool:
        return name in self.actions

    @property
    def resources(self) -> Optional[Path]:
        return self.folder / "resources" if self.folder else None

    def resource_url(self, name: str) -> str:
        return f"/static/plugins/{self._id}/resources/{name}"

    def settings(self) -> dict[str, Any]:
        return dict(self.saved)

    def save_settings(self, values: dict[str, Any]) -> None:
        self.saved.update(values)
