import asyncio
import base64
import json
from pathlib import Path
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.streamelements.astro_client import ASTRO_URL, AstroClient
from streamer_toolbox.connections.streamelements.astro_events import activity_events
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.gui.components.outside_link import outside_link
from streamer_toolbox.gui.components.secret_input import SecretInput

TOKEN_PAGE = "https://streamelements.com/dashboard/account/channels"


class StreamElementsConnection(ConnectionBase):
    """Listens to StreamElements' activity feed: tips (the one thing Twitch can't tell the toolbox), their store
    redemptions, merch and charity donations, and what the dashboard's test buttons send. Every activity becomes
    a `streamelements.activity` event for flows; a tip also the toolbox's `tip` event (Tip trigger, Tip alert,
    widgets). It only listens: nothing on the StreamElements account is changed.

    The token is the account's JWT (dashboard → profile → Channels → Show secrets). It gives full access to the
    account, so it's kept in its own file next to the settings (config/streamelements_token.txt: the JWT on line
    1, optionally the account id on line 2), never in toolbox.toml and never shown. Off until switched on."""

    id = "streamelements"
    title = "StreamElements"
    icon = "volunteer_activism"

    def __init__(self, settings: dict[str, Any], token_path: Path, events: EventBus, url: str = ASTRO_URL,
                 connect: Any = websockets.connect) -> None:
        super().__init__({}, settings)
        self._token_path = token_path
        self._events = events
        self._url = url
        self._connect = connect
        self._listener: asyncio.Task | None = None

    def fields(self) -> list[SettingField]:
        return []  # the token isn't typed into the tab: see add_gui_settings

    def add_gui_settings(self) -> None:
        SecretInput(self._token_path, "JWT Token", "token")
        ui.label("The token: your JWT Token (StreamElements dashboard → "
                 "your profile → Channels → Show secrets). It gives full access to your StreamElements account, so "
                 "treat it like a password. The toolbox only listens with it.").classes("text-sm opacity-80")
        outside_link("Open StreamElements' page with the token", TOKEN_PAGE).classes("text-sm")
        ui.label("What comes in: tips (also as the toolbox's Tip trigger and Tip alert), store redemptions, merch, "
                 "charity donations, and the dashboard's test buttons. Flows: the trigger \"StreamElements "
                 "activity\".").classes("text-xs opacity-60")

    async def start(self) -> None:
        await self.stop()
        try:
            token, room = self._read_token()
        except ValueError as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))
            return
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "connecting"))
        client = AstroClient(token, room, self._handle, self._state, self._url, self._connect)
        self._listener = asyncio.create_task(client.run())

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            await asyncio.gather(self._listener, return_exceptions=True)
            self._listener = None
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Connects once and asks for the activities: says whether StreamElements takes the token."""
        socket = None
        try:
            token, room = self._read_token()
            socket = await self._connect(self._url)
            await AstroClient(token, room, self._handle, url=self._url, connect=self._connect).subscribe(socket, 10)
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, str(e) or type(e).__name__)
        finally:
            if socket is not None:
                await socket.close()
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Feed", "activities"),))

    def _state(self, text: str) -> None:
        if text == "listening":
            self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (("Feed", "activities"),)))
        else:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, text))

    async def _handle(self, message: dict[str, Any]) -> None:
        for kind, data in activity_events(message):
            self._events.publish(kind, data)

    def _read_token(self) -> tuple[str, str]:
        """(the JWT, the account id: line 2, else the one inside the JWT)."""
        text = self._token_path.read_text(encoding="utf-8") if self._token_path.is_file() else ""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise ValueError("No token yet: type your StreamElements JWT Token into its field under Connections "
                             "→ StreamElements")
        return lines[0], lines[1] if len(lines) > 1 else _channel_in(lines[0])


def _channel_in(token: str) -> str:
    """The account id a JWT names (its `channel` claim), "" if it can't be read."""
    try:
        part = token.split(".")[1]
        return str(json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))).get("channel") or "")
    except (IndexError, ValueError):
        return ""
