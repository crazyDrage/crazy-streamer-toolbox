from collections.abc import Callable
from pathlib import Path
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.heartrate.heart_rate import HeartRate
from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.connections.websocket.request_socket import RequestSocket
from streamer_toolbox.core.connections.secret_file import SecretFile
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.gui.components.outside_link import outside_link
from streamer_toolbox.gui.components.secret_input import SecretInput

HYPERATE_URL = "wss://app.hyperate.io/socket/websocket?token="
KEY_PAGE = "https://www.hyperate.io/api"
DOCS = "https://github.com/HypeRate/DevDocs"
KEEP_ALIVE = (10.0, {"topic": "phoenix", "event": "heartbeat", "payload": {}, "ref": 0})  # their docs: every 10 s


class HypeRateConnection(LineConnection):
    """HypeRate (heart rate from a watch or chest strap): its websocket (github.com/HypeRate/DevDocs) tells
    every measurement of the HypeRate id typed on the tab, which the toolbox keeps as the heart rate
    (HeartRate: the `heartrate` event, the Get heart rate box). It only listens.

    HypeRate gives a websocket key on request (their API page); it is kept in its own file
    (config/secrets/hyperate_key.txt), never in toolbox.toml and never shown. Built from their docs, never run
    against the real service. Off until switched on."""

    id = "hyperate"
    title = "HypeRate"
    icon = "favorite"

    def __init__(self, settings: dict[str, Any], key_path: Path, heart: HeartRate, url: str = HYPERATE_URL,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0,
                 beat: tuple[float, dict[str, Any]] = KEEP_ALIVE) -> None:
        self._key = SecretFile(key_path, "websocket key", "HypeRate sends it on request, see the tab's link")
        self._heart = heart
        self._address = url
        super().__init__({"hyperate_id": ""}, settings, connect, retry_delay, beat)

    def fields(self) -> list[SettingField]:
        return [SettingField("hyperate_id", "Your HypeRate id", hint="the short code the HypeRate app shows "
                                                                    "(the end of your widget's address)")]

    def add_gui_settings(self) -> None:
        SecretInput(self._key, "Websocket key")
        ui.label("The websocket key: the key HypeRate gave you.").classes("text-sm opacity-80")
        outside_link("Ask HypeRate for a key", KEY_PAGE).classes("text-sm")
        outside_link("HypeRate's page about the feed", DOCS).classes("text-sm")
        ui.label("Not tried with the real service yet. What comes in: the heart rate. Flows: the trigger "
                 "\"Heart rate changed\" and the box Get heart rate.").classes("text-xs opacity-60")

    def _url(self, settings: dict[str, Any]) -> str:
        if not str(settings.get("hyperate_id") or "").strip():
            raise ValueError("No HypeRate id yet: type the id the HypeRate app shows")
        return self._address + self._key.read()

    def _hide(self, text: str) -> str:
        return self._key.hide(text)

    def _facts(self) -> tuple[tuple[str, str], ...]:
        return (("Feed", "heart rate"),)

    def _topic(self) -> str:
        return "hr:" + str(self._settings["hyperate_id"]).strip()

    async def _opened(self, line: RequestSocket) -> None:
        await line.send({"topic": self._topic(), "event": "phx_join", "payload": {}, "ref": 0})

    async def _message(self, message: dict[str, Any]) -> None:
        payload = message.get("payload")
        if message.get("event") == "hr_update" and message.get("topic") == self._topic() \
                and isinstance(payload, dict):
            self._heart.beat(payload.get("hr"), self.id)
