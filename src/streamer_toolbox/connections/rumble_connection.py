import asyncio
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from nicegui import ui

from streamer_toolbox.connections.rumble.rumble_feed import HOST, RumbleFeed
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.gui.components.outside_link import outside_link
from streamer_toolbox.gui.components.secret_input import SecretInput

KEY_PAGE = "https://rumble.com/account/livestream-api"
FASTEST = 2.0  # seconds; Rumble doesn't say how often it may be asked


class RumbleConnection(ConnectionBase):
    """Rumble, through its Live Stream API: follows, subscribers, gifted subs, and while a stream is live its
    chat messages and rants (paid messages). Each becomes a `rumble.…` event for flows; a rant also the
    toolbox's `tip` event (Tip trigger, Tip alert, widgets). Read only: Rumble's API has nothing to send with.

    The API is one address that holds the account's key. It is his account's, so it's kept in its own file next
    to the settings (config/rumble_address.txt), never in toolbox.toml and never shown. Off until switched on."""

    id = "rumble"
    title = "Rumble"
    icon = "smart_display"

    def __init__(self, settings: dict[str, Any], address_path: Path, events: EventBus,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__({"seconds": "5"}, settings)
        self._address_path = address_path
        self._events = events
        self._transport = transport
        self._listener: asyncio.Task | None = None

    def fields(self) -> list[SettingField]:
        return [SettingField("seconds", "Ask every (seconds)", hint="Rumble has no live feed: the toolbox asks "
                             f"again and again. Not faster than every {FASTEST:g} seconds.")]

    def add_gui_settings(self) -> None:
        SecretInput(self._address_path, "Live Stream API address", "address")
        ui.label("The address: your Live Stream API address "
                 "(Rumble → account → Live Stream API). It holds your key and can only read.") \
            .classes("text-sm opacity-80")
        outside_link("Open Rumble's page with the address", KEY_PAGE).classes("text-sm")
        ui.label("What comes in: follows, subscribers, gifted subs, and while you are live chat messages and "
                 "rants (a rant also as the toolbox's Tip trigger and Tip alert). Nothing can be sent to Rumble.") \
            .classes("text-xs opacity-60")

    async def start(self) -> None:
        await self.stop()
        try:
            address = self._read_address()
        except ValueError as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))
            return
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "connecting"))
        feed = RumbleFeed(address, self._handle, self._state, self._every(), self._transport)
        self._listener = asyncio.create_task(feed.run())

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            await asyncio.gather(self._listener, return_exceptions=True)
            self._listener = None
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Asks once: says whether Rumble takes the address, and how many follow the channel."""
        try:
            answer = await RumbleFeed(self._read_address(), self._handle, transport=self._transport).ask()
        except (ValueError, PermissionError, ConnectionError) as e:
            return ConnectionStatus(ConnectionState.ERROR, str(e))
        followers = answer.get("followers") if isinstance(answer.get("followers"), dict) else {}
        return ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("Followers", str(followers.get("num_followers_total", followers.get("num_followers", "?")))),))

    def _every(self) -> float:
        try:
            return max(float(self._settings["seconds"]), FASTEST)
        except (TypeError, ValueError):
            return 5.0

    def _state(self, text: str) -> None:
        if text == "listening":
            self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (("Feed", "events"),)))
        else:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, text))

    async def _handle(self, kind: str, data: dict[str, Any]) -> None:
        self._events.publish(kind, data)

    def _read_address(self) -> str:
        text = self._address_path.read_text(encoding="utf-8").strip() if self._address_path.is_file() else ""
        if not text:
            raise ValueError("No address yet: type your Rumble Live Stream API address into its field under "
                             "Connections → Rumble")
        address = text.splitlines()[0].strip()
        parts = urlsplit(address)
        # the key must only ever go to Rumble: a pasted wrong address is refused before anything is sent
        if parts.scheme != "https" or (parts.hostname or "") not in (HOST, "www." + HOST):
            raise ValueError(f"The file must hold an https://{HOST}/… address (your Live Stream API address)")
        return address
