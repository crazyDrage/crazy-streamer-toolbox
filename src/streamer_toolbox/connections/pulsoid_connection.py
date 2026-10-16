import asyncio
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import websockets
from nicegui import ui

from streamer_toolbox.connections.heartrate.heart_rate import HeartRate
from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.web.web_client import web_client
from streamer_toolbox.gui.components.outside_link import outside_link
from streamer_toolbox.gui.components.secret_input import SecretInput

PULSOID_URL = "wss://dev.pulsoid.net/api/v1/data/real_time?access_token="
WIDGET_CALL = "https://pulsoid.net/v1/api/public/rpc"  # what Pulsoid's own widget page asks; not in their API docs
WIDGET_LINK = re.compile(r"pulsoid\.net/widget/view/([0-9a-fA-F-]{36})")
DOCS = "https://docs.pulsoid.net/read-heart-rate/read-heart-rate-via-websocket"


class PulsoidConnection(LineConnection):
    """Pulsoid (heart rate from a watch or chest strap): its websocket tells every measurement, which the
    toolbox keeps as the heart rate (HeartRate: the `heartrate` event, the Get heart rate box). It only
    listens.

    Its file (config/secrets/pulsoid_token.txt, never in toolbox.toml and never shown) holds one of two things:
    - a token of his account that may read the heart rate (`data:heart_rate:read`); Pulsoid's docs don't say
      where a free account makes one by hand, and this way was never run against the real service;
    - or the link of one of his Pulsoid widgets (pulsoid.net/widget/view/...): the toolbox then asks Pulsoid
      what the widget page itself asks (WIDGET_CALL, `getWidget`) and listens where that says (`ramielUrl`,
      the same feed with the widget's own token). Tried on the real service (2026-10-10): the heart rate comes
      as {"data": {"heartRate": 51}}. It is Pulsoid's own widget call, not a documented one: it can change.
    Whoever has the link can read the heart rate, so it is kept like a token. Off until switched on."""

    id = "pulsoid"
    title = "Pulsoid"
    icon = "monitor_heart"

    def __init__(self, settings: dict[str, Any], token_path: Path, heart: HeartRate, url: str = PULSOID_URL,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0,
                 transport: httpx.AsyncBaseTransport | None = None, widget_call: str = WIDGET_CALL) -> None:
        self._token = SecretFile(token_path, "token or widget link", "from your Pulsoid account")
        self._heart = heart
        self._address = url
        self._transport = transport
        self._widget_call = widget_call
        self._feed = ""  # the widget's feed address, once Pulsoid told it
        self._finder: asyncio.Task | None = None
        super().__init__({}, settings, connect, retry_delay)

    def fields(self) -> list[SettingField]:
        return []

    def add_gui_settings(self) -> None:
        SecretInput(self._token, "Widget link or token")
        ui.label("The link of one of your Pulsoid "
                 "widgets (pulsoid.net/widget/view/...), or a Pulsoid token that may read the heart rate "
                 "(data:heart_rate:read). Keep the link to yourself: whoever has it can read your heart rate.") \
            .classes("text-sm opacity-80")
        outside_link("Pulsoid's page about the feed", DOCS).classes("text-sm")
        ui.label("The widget link was tried with the real service; a token was not. What comes in: the heart "
                 "rate. Flows: the trigger \"Heart rate changed\" and the box Get heart rate.") \
            .classes("text-xs opacity-60")

    async def start(self) -> None:
        await self.stop()
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "connecting"))
        self._finder = asyncio.create_task(self._find_then_listen())

    async def stop(self) -> None:
        if self._finder is not None:
            self._finder.cancel()
            await asyncio.gather(self._finder, return_exceptions=True)
            self._finder = None
        await super().stop()

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        try:
            await self._find_feed()
        except (ValueError, LookupError, ConnectionError) as e:
            return ConnectionStatus(ConnectionState.ERROR, str(e))
        return await super().test(settings)

    async def _find_then_listen(self) -> None:
        """A widget link first needs its feed address from Pulsoid. Tried again while the file is empty, Pulsoid
        knows no such widget or isn't reached: it goes on by itself once that is put right."""
        while True:
            try:
                await self._find_feed()
                break
            except (ValueError, LookupError, ConnectionError) as e:
                self._set_status(ConnectionStatus(ConnectionState.ERROR, f"{e}; trying again in "
                                                                         f"{self._retry_delay:.0f} s"))
                await asyncio.sleep(self._retry_delay)
        self._tasks = [asyncio.create_task(self._line.run())]

    async def _find_feed(self) -> None:
        self._feed = ""
        widget = WIDGET_LINK.search(self._token.read())
        if widget is None:
            return
        try:
            async with web_client(self._transport, timeout=10) as client:
                response = await client.post(self._widget_call, json={
                    "id": "1", "jsonrpc": "2.0", "method": "getWidget", "params": {"widgetId": widget.group(1)}})
            answer = response.json()
        except (httpx.HTTPError, ValueError) as e:
            raise ConnectionError(f"can't reach Pulsoid for the widget ({type(e).__name__})") from None
        result = answer.get("result") if isinstance(answer, dict) else None
        feed = str(result.get("ramielUrl") or "") if isinstance(result, dict) else ""
        if not feed.startswith(("wss://", "ws://")):
            raise LookupError("Pulsoid knows no widget with that link: copy the link again (Pulsoid → Widgets "
                              "→ the widget's link) into the field under Connections → Pulsoid")
        self._feed = feed

    def _url(self, settings: dict[str, Any]) -> str:
        return self._feed or self._address + self._token.read()

    def _hide(self, text: str) -> str:
        hidden = self._token.hide(text)
        return hidden.replace(self._feed, "<the widget's feed>") if self._feed else hidden

    def _facts(self) -> tuple[tuple[str, str], ...]:
        return (("Feed", "heart rate, from the widget link" if self._feed else "heart rate"),)

    async def _message(self, message: dict[str, Any]) -> None:
        data = message.get("data")
        if isinstance(data, dict):  # a token's feed says heart_rate, a widget's (the older form) heartRate
            self._heart.beat(data.get("heart_rate", data.get("heartRate")), self.id)
