import asyncio
from pathlib import Path
from typing import Any

import httpx
from nicegui import ui

from streamer_toolbox.connections.tiltify.tiltify_feed import EVENT, TiltifyFeed
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.gui.components.outside_link import outside_link
from streamer_toolbox.gui.components.secret_input import SecretInput

APPS = "https://app.tiltify.com/developers"
FASTEST = 5.0  # seconds; a fundraiser doesn't need faster, and Tiltify limits how often it may be asked


class TiltifyConnection(ConnectionBase):
    """Tiltify (charity fundraising): each new donation to one campaign becomes a `tiltify.donation` event
    (trigger "Tiltify donation"). It is NOT published as the toolbox's `tip`: the money goes to the charity,
    so tip alerts, tip totals and top tippers stay untouched. Read only.

    Tiltify wants an application of the streamer's own (their developer page): its Client ID is typed on the
    tab, its secret is kept in its own file (config/secrets/tiltify_secret.txt), never in toolbox.toml and never
    shown. Built from Tiltify's API reference, never run against the real service. NOT CONFIRMED: that every
    answer wraps its content in `data`, and that the login wants `scope=public`. Off until switched on."""

    id = "tiltify"
    title = "Tiltify"
    icon = "volunteer_activism"

    def __init__(self, settings: dict[str, Any], secret_path: Path, events: EventBus,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__({"client_id": "", "user": "", "campaign": "", "seconds": "15"}, settings)
        self._secret = SecretFile(secret_path, "client secret", "of your Tiltify application")
        self._events = events
        self._transport = transport
        self._listener: asyncio.Task | None = None

    def fields(self) -> list[SettingField]:
        return [SettingField("client_id", "Client ID", hint="of your Tiltify application"),
                SettingField("user", "User", hint="as in the campaign's address: tiltify.com/@<user>/<campaign>"),
                SettingField("campaign", "Campaign", hint="the last part of the campaign's address"),
                SettingField("seconds", "Ask every (seconds)", hint="Tiltify has no live feed for a program on "
                             f"a PC: the toolbox asks again and again. Not faster than every {FASTEST:g} seconds.")]

    def add_gui_settings(self) -> None:
        SecretInput(self._secret, "Client secret")
        ui.label("The client secret: the secret of your Tiltify application.").classes("text-sm opacity-80")
        outside_link("Tiltify's page for applications", APPS).classes("text-sm")
        ui.label("Not tried with the real service yet. What comes in: each new donation to the campaign, as "
                 "the trigger \"Tiltify donation\" (not as a tip: it is the charity's money).") \
            .classes("text-xs opacity-60")

    async def start(self) -> None:
        await self.stop()
        try:
            feed = self._feed(self._settings)
        except ValueError as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))
            return
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "connecting"))
        self._listener = asyncio.create_task(feed.run())

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            await asyncio.gather(self._listener, return_exceptions=True)
            self._listener = None
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Logs in and looks the campaign up once."""
        try:
            campaign = await self._feed(settings).campaign()
        except (ValueError, PermissionError, LookupError, ConnectionError) as e:
            return ConnectionStatus(ConnectionState.ERROR, self._secret.hide(str(e)))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Campaign", str(campaign.get("name") or "?")),))

    def _feed(self, settings: dict[str, Any]) -> TiltifyFeed:
        named = {key: str(settings.get(key) or "").strip().lstrip("@") for key in ("client_id", "user", "campaign")}
        missing = [key.replace("_", " ") for key, value in named.items() if not value]
        if missing:
            raise ValueError(f"Not set yet: {', '.join(missing)}")
        return TiltifyFeed(named["client_id"], self._secret.read(), named["user"], named["campaign"],
                           self._handle, self._state, self._every(settings), self._transport)

    @staticmethod
    def _every(settings: dict[str, Any]) -> float:
        try:
            return max(float(settings["seconds"]), FASTEST)
        except (TypeError, ValueError):
            return 15.0

    def _state(self, text: str) -> None:
        if text == "listening":
            self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (("Feed", "donations"),)))
        else:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, self._secret.hide(text)))

    async def _handle(self, data: dict[str, Any]) -> None:
        self._events.publish(EVENT, data)
