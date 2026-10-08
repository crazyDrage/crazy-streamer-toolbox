import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.streamerbot.streamerbot_actions import StreamerbotActions
from streamer_toolbox.connections.streamerbot.streamerbot_events import EVENT, authentication, streamerbot_event
from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.connections.websocket.request_socket import RequestSocket
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus

DOCS = "https://docs.streamer.bot/api/websocket"


class StreamerbotConnection(LineConnection):
    """Streamer.bot, over its WebSocket server (Servers/Clients → WebSocket Server, port 8080): the toolbox
    runs its actions by name, reads its globals, and gets told its events as `streamerbot.event` (trigger
    "Streamer.bot event", by source and type). Which events: the categories named on the tab; Twitch is left
    out by default because the toolbox has its own Twitch connection, and Kick is in because the toolbox has
    none.

    A password is only needed when Streamer.bot's server asks for one; it is kept in its own file
    (config/streamerbot_password.txt). Built from Streamer.bot's docs, never run against the real program.
    Off until switched on."""

    id = "streamerbot"
    title = "Streamer.bot"
    icon = "precision_manufacturing"

    def __init__(self, settings: dict[str, Any], password_path: Path, events: EventBus,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0) -> None:
        self._password = SecretFile(password_path, "password", "Streamer.bot → Servers/Clients → WebSocket Server")
        self._events = events
        self._hello: dict[str, Any] = {}
        self._greeted = asyncio.Event()
        self._listening: list[str] = []
        super().__init__({"url": "ws://127.0.0.1:8080/", "listen": "Kick, Custom, General"}, settings, connect,
                         retry_delay)

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address", hint="Streamer.bot → Servers/Clients → WebSocket Server: "
                                                    "Start Server (and Auto Start)"),
                SettingField("listen", "Events to listen to", hint="Streamer.bot's event categories, with "
                             "commas: Kick, Custom, General, YouTube, ... or * for all. Twitch comes twice if "
                             "the toolbox's own Twitch connection is on too")]

    def add_gui_settings(self) -> None:
        ui.label(f"Only if Streamer.bot's WebSocket server has Authentication on: put its password into "
                 f"{self._password.path}, nothing else in the file.").classes("text-sm opacity-80")
        ui.label("Not tried with the real program yet. Boxes: Run Streamer.bot action (picked from a list), "
                 "Get global, Write in chat. Trigger: \"Streamer.bot event\".").classes("text-xs opacity-60")
        ui.link("Streamer.bot's page about it", DOCS, new_tab=True).classes("text-sm")

    def add_actions(self, actions: ActionRegistry) -> None:
        StreamerbotActions(self._request).add_to(actions)

    def _url(self, settings: dict[str, Any]) -> str:
        return str(settings["url"]).strip()

    def _hide(self, text: str) -> str:
        return self._password.hide(text)

    def _facts(self) -> tuple[tuple[str, str], ...]:
        info = self._hello.get("info") if isinstance(self._hello.get("info"), dict) else {}
        return (("Streamer.bot", str(info.get("version") or "?")),
                ("Listening to", ", ".join(self._listening) or "nothing"))

    async def _request(self, message: dict[str, Any]) -> dict[str, Any]:
        return _ok(await self._ask(message))

    async def _opened(self, line: RequestSocket) -> None:
        try:  # Streamer.bot greets first; an older one that doesn't is taken as "no password"
            await asyncio.wait_for(self._greeted.wait(), 2)
        except TimeoutError:
            self._hello = {}
        self._greeted.clear()
        asked = self._hello.get("authentication")
        if isinstance(asked, dict):
            password = self._password.read_or_empty()
            if not password:
                raise PermissionError(f"Streamer.bot asks for a password: put it into {self._password.path}")
            answer = await line.request({"request": "Authenticate", "authentication": authentication(
                password, str(asked.get("salt") or ""), str(asked.get("challenge") or ""))})
            if answer.get("status") != "ok":
                raise PermissionError("Streamer.bot refused the password")
        known = _ok(await line.request({"request": "GetEvents"})).get("events")
        wanted = self._wanted(known if isinstance(known, dict) else {})
        if wanted:
            _ok(await line.request({"request": "Subscribe", "events": wanted}))
        self._listening = sorted(wanted)

    def _wanted(self, known: dict[str, Any]) -> dict[str, list[str]]:
        """The categories named in the settings, as Streamer.bot spells them, each with all its events."""
        names = {n.strip().casefold() for n in str(self._settings["listen"]).split(",") if n.strip()}
        return {category: list(events) for category, events in known.items()
                if isinstance(events, list) and ("*" in names or category.casefold() in names)}

    async def _message(self, message: dict[str, Any]) -> None:
        if message.get("request") == "Hello":
            self._hello = message
            self._greeted.set()
        elif isinstance(message.get("event"), dict):
            self._events.publish(EVENT, streamerbot_event(message))


def _ok(answer: dict[str, Any]) -> dict[str, Any]:
    if answer.get("status") not in (None, "ok"):
        raise RuntimeError(f"Streamer.bot: {answer.get('error') or answer.get('status')}")
    return answer
