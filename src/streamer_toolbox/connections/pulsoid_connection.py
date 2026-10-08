from collections.abc import Callable
from pathlib import Path
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.heartrate.heart_rate import HeartRate
from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.setting_field import SettingField

PULSOID_URL = "wss://dev.pulsoid.net/api/v1/data/real_time?access_token="
DOCS = "https://docs.pulsoid.net/read-heart-rate/read-heart-rate-via-websocket"


class PulsoidConnection(LineConnection):
    """Pulsoid (heart rate from a watch or chest strap): its websocket tells every measurement, which the
    toolbox keeps as the heart rate (HeartRate: the `heartrate` event, the Get heart rate box). It only
    listens.

    The token is his account's (it needs the permission to read the heart rate, `data:heart_rate:read`):
    kept in its own file (config/pulsoid_token.txt), never in toolbox.toml and never shown. Built from
    Pulsoid's docs, never run against the real service; their docs don't say where a token is made by hand.
    Off until switched on."""

    id = "pulsoid"
    title = "Pulsoid"
    icon = "monitor_heart"

    def __init__(self, settings: dict[str, Any], token_path: Path, heart: HeartRate, url: str = PULSOID_URL,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0) -> None:
        self._token = SecretFile(token_path, "token", "from your Pulsoid account")
        self._heart = heart
        self._address = url
        super().__init__({}, settings, connect, retry_delay)

    def fields(self) -> list[SettingField]:
        return []

    def add_gui_settings(self) -> None:
        ui.label(f"The token is read from {self._token.path}: a Pulsoid token that may read the heart rate "
                 "(data:heart_rate:read), nothing else in the file.").classes("text-sm opacity-80")
        ui.link("Pulsoid's page about the feed", DOCS, new_tab=True).classes("text-sm")
        ui.label("Not tried with the real service yet. What comes in: the heart rate. Flows: the trigger "
                 "\"Heart rate changed\" and the box Get heart rate.").classes("text-xs opacity-60")

    def _url(self, settings: dict[str, Any]) -> str:
        return self._address + self._token.read()

    def _hide(self, text: str) -> str:
        return self._token.hide(text)

    def _facts(self) -> tuple[tuple[str, str], ...]:
        return (("Feed", "heart rate"),)

    async def _message(self, message: dict[str, Any]) -> None:
        data = message.get("data")
        if isinstance(data, dict):
            self._heart.beat(data.get("heart_rate"), self.id)
