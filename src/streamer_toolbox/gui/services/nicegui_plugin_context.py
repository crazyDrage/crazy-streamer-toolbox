from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter
from nicegui import app, ui

from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.actions.registered_action import ActionHandler, OptionsProvider
from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.secrets_folder import SecretsFolder
from streamer_toolbox.core.events.event_bus import EventBus, EventHandler
from streamer_toolbox.core.events.event_fields import EVENT_FIELDS
from streamer_toolbox.core.flows.box_signals import BoxSignals
from streamer_toolbox.core.flows.retrigger import Retrigger, current_retrigger
from streamer_toolbox.core.interfaces.confirm_service import ConfirmService
from streamer_toolbox.core.interfaces.connection import Connection
from streamer_toolbox.core.interfaces.field_editor import FieldEditor
from streamer_toolbox.gui.components.flow_editor.trigger_kinds import (TRIGGER_CHOICES, TRIGGER_INFO,
                                                                       TRIGGER_KINDS)
from streamer_toolbox.gui.components.flow_editor.value_editors import add_editor
from streamer_toolbox.gui.services.ui_registry import SECTIONS, UiRegistry
from streamer_toolbox.core.actions.json_boxes import JsonBoxes, Send
from streamer_toolbox.core.values.value_kind import ValueKind
from streamer_toolbox.core.values.value_kinds import ValueKinds
from streamer_toolbox.core.web.web_boxes import WebBoxes
from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.plugins.plugin_settings import PluginSettings

PageFrame = Callable[[str, str, Callable[[], None]], None]  # title, path, builder


class NiceGuiPluginContext(PluginContext):
    """PluginContext on top of NiceGUI/FastAPI: one app serves the API, the pages and the plugin files."""

    def __init__(self, plugin_id: str, actions: ActionRegistry, ui_registry: UiRegistry,
                 confirm: ConfirmService, page_frame: PageFrame, folder: Optional[Path] = None,
                 config_folder: Optional[Path] = None, events: Optional[EventBus] = None,
                 secrets: Optional[SecretsFolder] = None, is_on: Callable[[], bool] = lambda: True) -> None:
        self._id = plugin_id
        self._is_on = is_on  # switched off on the Plugins page: its triggers, listeners and page are quiet
        self._secrets = secrets or SecretsFolder(config_folder or Path("config"))
        self._events = events or EventBus()
        self._actions = actions
        self._ui = ui_registry
        self._confirm = confirm
        self._page_frame = page_frame
        self._static_count = 0
        self._resources = folder / "resources" if folder else None
        self._resources_url = f"/static/plugins/{plugin_id}/resources"
        if self._resources and self._resources.is_dir():
            app.add_static_files(self._resources_url, self._resources)
        saved = (config_folder or Path("config")) / "plugins" / f"{plugin_id}.json"
        self._settings = PluginSettings(self._resources / "settings.json" if self._resources else None, saved)

    @property
    def plugin_id(self) -> str:
        return self._id

    def add_action(self, name: str, handler: ActionHandler, description: str = "", label: str = "",
                   **box: Any) -> None:
        self._actions.add(f"{self._id}.{name}", handler, description, label, **box)

    def box_signals(self) -> Optional[BoxSignals]:
        return BoxSignals.current()

    def retrigger(self) -> Optional[Retrigger]:
        return current_retrigger.get()

    def add_field_editor(self, kind: str, editor: type[FieldEditor]) -> str:
        add_editor(f"{self._id}.{kind}", editor)
        return f"{self._id}.{kind}"

    def add_json_boxes(self, folder: Path, send: Send, kinds: Collection[ValueKind] = ()) -> None:
        JsonBoxes(folder, ValueKinds(kinds)).add_to(self._actions, self._id, send)

    def secret(self, name: str, label: str, hint: str = "") -> SecretFile:
        for plugin_id, _, _, known in self._ui.secrets:
            if plugin_id == self._id and known.path.name == f"{self._id}_{name}.txt":
                return known
        file = SecretFile(self._secrets.path(f"{self._id}_{name}.txt"), label,
                          field=f"its field on the plugin's card (Plugins → {self._id})")
        self._ui.secrets.append((self._id, label, hint, file))
        return file

    def add_web_boxes(self, folder: Path) -> None:
        WebBoxes(folder, secret=self.secret).add_to(self._actions, self._id)

    def add_connection(self, connection: Connection) -> None:
        if connection.id != self._id:
            raise ValueError(f"a plugin's connection must have the plugin's id ({self._id!r}, not "
                             f"{connection.id!r})")
        if any(known.id == connection.id for known in self._ui.connections):
            raise ValueError("a plugin can add one connection")
        self._ui.connections.append(connection)

    def add_trigger(self, event: str, title: str, fields: tuple[str, ...], icon: str = "bolt", pick: str = "",
                    example: str = "*", description: str = "",
                    choices: OptionsProvider | Collection[str] | None = None) -> str:
        kind = f"{self._id}.{event}"
        if not fields:
            raise ValueError("a trigger needs at least one field")
        EVENT_FIELDS[kind] = tuple(fields)
        TRIGGER_KINDS[kind] = (icon, title, pick or fields[0], example)
        if description:
            TRIGGER_INFO[kind] = description
        if choices is not None:
            TRIGGER_CHOICES[kind] = choices if callable(choices) else _fixed(choices)
        return kind

    def publish(self, event: str, data: dict[str, Any]) -> None:
        if self._is_on():
            self._events.publish(f"{self._id}.{event}", dict(data))

    def on_event(self, handler: EventHandler) -> None:
        async def heard(kind: str, data: dict[str, Any]) -> None:
            if self._is_on():
                await handler(kind, data)

        self._events.subscribe(heard)

    def add_router(self, router: APIRouter) -> None:
        app.include_router(router, prefix=f"/api/plugins/{self._id}")

    def add_page(self, title: str, builder: Callable[[], None], subpath: str = "", icon: str = "extension") -> str:
        path = f"/plugins/{self._id}" + (f"/{subpath.strip('/')}" if subpath else "")
        ui.page(path, title=f"{title} · {APP_NAME}")(lambda: self._page_frame(title, path, self._unless_off(builder)))
        if not subpath:
            self._ui.pages.append((title, path, icon))
        return path

    def _unless_off(self, builder: Callable[[], None]) -> Callable[[], None]:
        def build() -> None:
            if self._is_on():
                builder()
            else:
                ui.label(f"The plugin {self._id} is switched off. Switch it on under Plugins.").classes("opacity-70")
        return build

    def add_panel(self, title: str, builder: Callable[[], None], section: str = "live") -> None:
        if section not in SECTIONS:
            raise ValueError(f"section must be one of {', '.join(SECTIONS)} (got {section!r})")
        self._ui.panels.append((self._id, section, title, builder))

    def add_static(self, folder: Path) -> str:
        self._static_count += 1
        # not under /static: that mount comes first and would answer 404 for a folder added while running
        url = f"/plugin-static/{self._id}" + (f"-{self._static_count}" if self._static_count > 1 else "")
        app.add_static_files(url, folder)
        return url

    async def ask_yes_no(self, question: str, timeout: float = 20.0) -> Optional[bool]:
        return await self._confirm.ask(question, timeout)

    def add_tool(self, title: str, builder: Callable[[], None], icon: str = "build", description: str = "") -> None:
        self._ui.tools.append((self._id, title, icon, description, builder))

    async def run_action(self, name: str, **params: Any) -> Any:
        return await self._actions.run(name, **params)

    def has_action(self, name: str) -> bool:
        return name in self._actions

    @property
    def resources(self) -> Optional[Path]:
        return self._resources

    def resource_url(self, name: str) -> str:
        return f"{self._resources_url}/{name.lstrip('/')}"

    def settings(self) -> dict[str, Any]:
        return self._settings.load()

    def save_settings(self, values: dict[str, Any]) -> None:
        self._settings.save(values)


def _fixed(choices: Collection[str]) -> OptionsProvider:
    """A list of choices as the function the flow editor asks."""
    async def same() -> list[str]:
        return list(choices)

    return same
