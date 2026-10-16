import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.streamlabs.streamlabs_events import streamlabs_events
from streamer_toolbox.connections.streamlabs.streamlabs_socket import STREAMLABS_URL, StreamlabsSocket
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.gui.components.outside_link import outside_link
from streamer_toolbox.gui.components.secret_input import SecretInput

TOKEN_PAGE = "https://streamlabs.com/dashboard#/settings/api-settings"


class StreamlabsConnection(ConnectionBase):
    """Listens to Streamlabs' socket: donations (the one thing Twitch can't tell the toolbox), their store
    redemptions, merch, Twitch charity donations, what the Alert Box's test buttons send, and the events of every
    platform linked to the Streamlabs account (YouTube: Super Chats, Super Stickers, memberships, gifts). Every
    activity becomes a `streamlabs.activity` event for flows, with its platform; a donation, Super Chat or Super
    Sticker also the toolbox's `tip` event (Tip trigger, Tip alert, widgets). It only listens.

    The token is the Socket API Token (dashboard → Settings → API Settings → API Tokens). It can only listen, but
    it's still his account's: kept in its own file next to the settings (config/secrets/streamlabs_token.txt), never in
    toolbox.toml and never shown. Off until switched on."""

    id = "streamlabs"
    title = "Streamlabs"
    icon = "savings"

    def __init__(self, settings: dict[str, Any], token_path: Path, events: EventBus, url: str = STREAMLABS_URL,
                 connect: Any = websockets.connect,
                 raw: Callable[[str, dict[str, Any]], None] | None = None) -> None:
        super().__init__({}, settings)
        self._token_path = token_path
        self._events = events
        self._url = url
        self._connect = connect
        self._raw = raw  # gets (event name, Streamlabs' own message) right before the event goes out
        self._listener: asyncio.Task | None = None

    def fields(self) -> list[SettingField]:
        return []  # the token isn't typed into the tab: see add_gui_settings

    def add_gui_settings(self) -> None:
        SecretInput(self._token_path, "Socket API Token", "token")
        ui.label("The token: your Socket API Token "
                 "(Streamlabs dashboard → Settings → API Settings → API Tokens). It can only listen to your "
                 "events.").classes("text-sm opacity-80")
        outside_link("Open Streamlabs' page with the token", TOKEN_PAGE).classes("text-sm")
        ui.label("What comes in: donations, YouTube Super Chats and Super Stickers (all three also as the "
                 "toolbox's Tip trigger and Tip alert), store redemptions, merch, Twitch charity donations, YouTube "
                 "memberships and gifts, and the Alert Box's test buttons. Flows: the trigger \"Streamlabs "
                 "activity\" (its platform says twitch, youtube or streamlabs).").classes("text-xs opacity-60")

    async def start(self) -> None:
        await self.stop()
        try:
            token = self._read_token()
        except ValueError as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))
            return
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "connecting"))
        socket = StreamlabsSocket(token, self._handle, self._state, self._url, self._connect)
        self._listener = asyncio.create_task(socket.run())

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            await asyncio.gather(self._listener, return_exceptions=True)
            self._listener = None
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Connects once: says whether Streamlabs takes the token."""
        socket, token = None, ""
        try:
            token = self._read_token()
            socket = await self._connect(self._url + token)
            await StreamlabsSocket(token, self._handle).open(socket, 10)
        except Exception as e:
            reason = str(e).replace(token, "<token>") if token else str(e)
            return ConnectionStatus(ConnectionState.ERROR, reason or type(e).__name__)
        finally:
            if socket is not None:
                await socket.close()
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Feed", "events"),))

    def _state(self, text: str) -> None:
        if text == "listening":
            self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (("Feed", "events"),)))
        else:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, text))

    async def _handle(self, payload: dict[str, Any]) -> None:
        for kind, data in streamlabs_events(payload):
            if self._raw is not None:
                self._raw(kind, payload)
            self._events.publish(kind, data)

    def _read_token(self) -> str:
        text = self._token_path.read_text(encoding="utf-8").strip() if self._token_path.is_file() else ""
        if not text:
            raise ValueError("No token yet: type your Streamlabs Socket API Token into its field under Connections "
                             "→ Streamlabs")
        return text.splitlines()[0].strip()
