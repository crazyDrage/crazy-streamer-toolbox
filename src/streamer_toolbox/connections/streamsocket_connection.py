import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.streamsocket.streamsocket_client import EVENT, STREAMSOCKET_URL, StreamSocketClient
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus

EXTENSION = "https://dashboard.twitch.tv/extensions/1lpj3883m4u6exlgdwzuk627bvpabj"
DOCS = "https://streamsocket.kadokta.com/"


class StreamSocketConnection(ConnectionBase):
    """The Twitch extension "StreamSocket Events": viewers press a button in the extension (for bits or for
    free) and the toolbox gets it as a `streamsocket.event` (trigger "StreamSocket event", by the event's name),
    like a channel point redeem that lives in an extension. It only listens.

    The secret comes from the extension's configuration page and is his: kept in its own file next to the
    settings (config/streamsocket_secret.txt), never in toolbox.toml and never shown. The channel is his Twitch
    id: the one typed on the tab, else the one of the toolbox's Twitch login. Off until switched on."""

    id = "streamsocket"
    title = "StreamSocket Events"
    icon = "extension"

    def __init__(self, settings: dict[str, Any], secret_path: Path, events: EventBus,
                 twitch_id: Callable[[], str] = lambda: "", url: str = STREAMSOCKET_URL,
                 connect: Any = websockets.connect) -> None:
        super().__init__({"channel_id": ""}, settings)
        self._secret_path = secret_path
        self._events = events
        self._twitch_id = twitch_id
        self._url = url
        self._connect = connect
        self._listener: asyncio.Task | None = None

    def fields(self) -> list[SettingField]:
        return [SettingField("channel_id", "Twitch channel id (numbers)",
                             hint="leave empty to use the channel of the toolbox's Twitch login")]

    def add_gui_settings(self) -> None:
        ui.label(f"The secret is read from {self._secret_path}: the secret from the extension's configuration "
                 "page, nothing else in the file. It lets a program listen to your extension's events.") \
            .classes("text-sm opacity-80")
        ui.link("Open the extension on Twitch", EXTENSION, new_tab=True).classes("text-sm")
        ui.link("StreamSocket Events' own page", DOCS, new_tab=True).classes("text-sm")
        ui.label("What comes in: each event a viewer redeems in the extension, with its name, the viewer and "
                 "the bits it cost. Flows: the trigger \"StreamSocket event\".").classes("text-xs opacity-60")

    async def start(self) -> None:
        await self.stop()
        try:
            client = self._client(self._settings)
        except ValueError as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))
            return
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "connecting"))
        self._listener = asyncio.create_task(client.run())

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            await asyncio.gather(self._listener, return_exceptions=True)
            self._listener = None
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Connects once: says whether the server takes the secret for that channel."""
        socket, secret = None, ""
        try:
            client = self._client(settings)
            secret = self._read_secret()
            socket = await self._connect(self._url + self._channel(settings))
            await client.check(socket, 10)
        except Exception as e:
            reason = str(e).replace(secret, "<secret>") if secret else str(e)
            return ConnectionStatus(ConnectionState.ERROR, reason or type(e).__name__)
        finally:
            if socket is not None:
                await socket.close()
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Channel", self._channel(settings)),))

    def _client(self, settings: dict[str, Any]) -> StreamSocketClient:
        return StreamSocketClient(self._channel(settings), self._read_secret(), self._handle, self._state,
                                  self._url, self._connect)

    def _channel(self, settings: dict[str, Any]) -> str:
        channel = str(settings.get("channel_id") or "").strip() or str(self._twitch_id() or "").strip()
        if not channel.isdigit():
            raise ValueError("No channel yet: connect Twitch first, or type your Twitch channel id (numbers)")
        return channel

    def _state(self, text: str) -> None:
        if text == "listening":
            self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (("Feed", "events"),)))
        else:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, text))

    async def _handle(self, data: dict[str, Any]) -> None:
        self._events.publish(EVENT, data)

    def _read_secret(self) -> str:
        text = self._secret_path.read_text(encoding="utf-8").strip() if self._secret_path.is_file() else ""
        if not text:
            raise ValueError(f"No secret yet: put the secret from the extension's configuration page into "
                             f"{self._secret_path}")
        return text.splitlines()[0].strip()
