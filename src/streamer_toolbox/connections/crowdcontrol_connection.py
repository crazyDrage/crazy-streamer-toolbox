from collections.abc import Callable
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.connections.websocket.request_socket import RequestSocket
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus

CROWD_CONTROL_URL = "wss://pubsub.crowdcontrol.live/"
DOCS = "https://developer.crowdcontrol.live/sockets"
EVENT = "crowdcontrol.effect"
STATUS = {"effect-request": "requested", "effect-success": "succeeded", "effect-failure": "failed"}
KEEP_ALIVE = (540.0, {"action": "ping"})  # their docs: the line drops after 10 quiet minutes


def connect_named(url: str) -> Any:
    """Crowd Control asks every program to name itself when it connects."""
    return websockets.connect(url, user_agent_header="streamer-toolbox")


class CrowdControlConnection(LineConnection):
    """Crowd Control (viewers buy effects in the streamer's game): its PubSub websocket tells what happens
    on a streamer's public topic, `pub/ccuid-<id>`, without a login. Each effect a viewer asks for, and
    whether the game did it, becomes a `crowdcontrol.effect` event (trigger "Crowd Control effect"; `status`
    is requested, succeeded or failed). It only listens.

    Built from Crowd Control's docs, never run against the real service. NOT CONFIRMED: the docs show an
    effect request in full and say a success / failure looks the same; and they don't say where a streamer
    reads their own id (it starts with "ccuid-"). Off until switched on."""

    id = "crowdcontrol"
    title = "Crowd Control"
    icon = "sports_esports"

    def __init__(self, settings: dict[str, Any], events: EventBus, url: str = CROWD_CONTROL_URL,
                 connect: Callable[..., Any] = connect_named, retry_delay: float = 5.0) -> None:
        self._events = events
        self._address = url
        super().__init__({"ccuid": ""}, settings, connect, retry_delay, KEEP_ALIVE)

    def fields(self) -> list[SettingField]:
        return [SettingField("ccuid", "Your Crowd Control id", hint="starts with ccuid-")]

    def add_gui_settings(self) -> None:
        ui.label("Not tried with the real service yet. What comes in: each effect a viewer asks for, and "
                 "whether the game did it. Flows: the trigger \"Crowd Control effect\".") \
            .classes("text-sm opacity-80")
        ui.link("Crowd Control's page about the feed", DOCS, new_tab=True).classes("text-sm")

    def _url(self, settings: dict[str, Any]) -> str:
        if not self._topic(settings):
            raise ValueError("No Crowd Control id yet: type your id (it starts with ccuid-)")
        return self._address

    @staticmethod
    def _topic(settings: dict[str, Any]) -> str:
        ccuid = str(settings.get("ccuid") or "").strip()
        if not ccuid:
            return ""
        return "pub/" + (ccuid if ccuid.startswith("ccuid-") else "ccuid-" + ccuid)

    def _facts(self) -> tuple[tuple[str, str], ...]:
        return (("Feed", "effects"),)

    async def _opened(self, line: RequestSocket) -> None:
        await line.send({"action": "subscribe", "data": {"topics": [self._topic(self._settings)]}})

    async def _message(self, message: dict[str, Any]) -> None:
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        if message.get("type") == "subscription-result" and payload.get("failure"):
            self._state("Crowd Control doesn't know this id: check it on the tab")
        status = STATUS.get(str(message.get("type") or ""))
        if status is not None and message.get("domain") == "pub":
            self._events.publish(EVENT, crowd_control_effect(status, payload))


def crowd_control_effect(status: str, payload: dict[str, Any]) -> dict[str, Any]:
    """An effect message's payload as the toolbox's `crowdcontrol.effect`."""
    def part(name: str) -> dict[str, Any]:
        return payload[name] if isinstance(payload.get(name), dict) else {}

    effect = part("effect")
    return {"status": status, "effect": str(effect.get("name") or effect.get("effectID") or ""),
            "effect_id": str(effect.get("effectID") or ""), "game": str(part("game").get("name") or ""),
            "user": str(part("requester").get("name") or ""), "target": str(part("target").get("name") or ""),
            "seconds": effect.get("duration") or 0, "request_id": str(payload.get("requestID") or "")}
