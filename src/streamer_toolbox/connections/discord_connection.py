from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from nicegui import ui

from streamer_toolbox.connections.discord.discord_actions import DiscordActions
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.gui.components.outside_link import outside_link
from streamer_toolbox.gui.components.secret_input import SecretInput

HOSTS = ("discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com")
HELP = "https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks"


class DiscordConnection(ConnectionBase):
    """Discord, through a channel's webhook: the toolbox posts messages into that one channel
    (DiscordActions). No bot, no login, nothing is read.

    The webhook's address lets anyone who has it post there, so it is kept in its own file
    (config/discord_webhook.txt), never in toolbox.toml, and never put into an error text or a log. Built
    from what is known of Discord's webhooks, never run against the real service. Off until switched on."""

    id = "discord"
    title = "Discord"
    icon = "forum"

    def __init__(self, settings: dict[str, Any], webhook_path: Path,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__({}, settings)
        self._webhook = SecretFile(webhook_path, "webhook address",
                                   "Discord → the channel's settings → Integrations → Webhooks")
        self._transport = transport

    def fields(self) -> list[SettingField]:
        return []

    def add_gui_settings(self) -> None:
        SecretInput(self._webhook, "Webhook address")
        ui.label("The webhook's address: Discord → the channel's settings "
                 "→ Integrations → Webhooks → New Webhook → Copy Webhook URL. "
                 "Whoever has it can post in that channel.").classes("text-sm opacity-80")
        outside_link("Discord's page about webhooks", HELP).classes("text-sm")
        ui.label("Not tried with the real service yet. Box: Post to Discord.").classes("text-xs opacity-60")

    async def start(self) -> None:
        self._set_status(await self.test(self._settings))

    async def stop(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Asks Discord about the webhook: says whether the address is right. Posts nothing."""
        try:
            about = await self._call("GET")
        except (ValueError, ConnectionError, RuntimeError) as e:
            return ConnectionStatus(ConnectionState.ERROR, str(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Webhook", str(about.get("name") or "?")),))

    def add_actions(self, actions: ActionRegistry) -> None:
        DiscordActions(self._post).add_to(actions)

    async def _post(self, body: dict[str, Any]) -> None:
        if not self._settings["enabled"]:
            raise NotConnectedError("Discord is switched off under Connections → Discord")
        try:
            await self._call("POST", json=body)
        except ValueError as e:
            raise NotConnectedError(str(e)) from None

    async def _call(self, method: str, **kwargs: Any) -> dict[str, Any]:
        """One call to the webhook. ValueError without a usable address, NotConnectedError when Discord
        doesn't answer, RuntimeError with Discord's words when it refuses."""
        address = self._address()
        try:
            async with web_client(self._transport, timeout=10) as client:
                response = await client.request(method, address, **kwargs)
        except httpx.HTTPError as e:  # its text would name the address
            raise NotConnectedError(f"can't reach Discord ({type(e).__name__})") from None
        try:
            answer = response.json() if response.content else {}
        except ValueError:
            answer = {}
        answer = answer if isinstance(answer, dict) else {}
        if response.status_code in (401, 403, 404):
            raise RuntimeError("Discord doesn't know this webhook: was it deleted? Copy its address again")
        if response.status_code >= 400:
            raise RuntimeError(f"Discord: {answer.get('message') or response.status_code}")
        return answer

    def _address(self) -> str:
        address = self._webhook.read()
        parts = urlsplit(address)
        # the address is a key: a pasted wrong one is refused before anything is sent anywhere
        if parts.scheme != "https" or (parts.hostname or "") not in HOSTS or "/api/webhooks/" not in parts.path:
            raise ValueError("The file must hold a https://discord.com/api/webhooks/… address")
        return address
