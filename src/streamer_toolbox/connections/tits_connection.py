from collections.abc import Callable
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.tits.tits_actions import TitsActions
from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.connections.websocket.request_socket import RequestSocket
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus

DOCS = "https://github.com/Remasuri/TITSAPI"
EVENTS = {"TITSHitEvent": "tits.hit", "TITSTriggerActivatedEvent": "tits.trigger_started",
          "TITSTriggerEndedEvent": "tits.trigger_ended"}


class TitsConnection(LineConnection):
    """Twitch Integrated Throwing System (T.I.T.S.): its public API (github.com/Remasuri/TITSAPI), a
    websocket for requests (`/websocket`) and one that tells what happens (`/events`). Boxes throw an item
    or activate a trigger (TitsActions); a hit on the model and a trigger starting / ending start flows
    (`tits.hit`, `tits.trigger_started`, `tits.trigger_ended`). No login.

    Built from the API's README, never run against the real program. NOT CONFIRMED: how T.I.T.S. words a
    refused request; any answer whose type says "Error" is taken as one. Off until switched on."""

    id = "tits"
    title = "T.I.T.S."
    icon = "sports_baseball"
    id_key = "requestID"

    def __init__(self, settings: dict[str, Any], events: EventBus,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0) -> None:
        self._events = events
        super().__init__({"url": "ws://localhost:42069"}, settings, connect, retry_delay)
        self._told = RequestSocket("T.I.T.S. events", lambda: self._base(self._settings) + "/events",
                                   self._event, connect=connect, retry_delay=retry_delay)

    def fields(self) -> list[SettingField]:
        return [SettingField("url", "Address", hint="T.I.T.S. → Settings: the API must be switched on")]

    def add_gui_settings(self) -> None:
        ui.label("Not tried with the real program yet. Boxes: Throw item, Activate trigger. Triggers: "
                 "\"T.I.T.S. model was hit\", \"T.I.T.S. trigger started / ended\".").classes("text-sm opacity-80")
        ui.link("The API's page", DOCS, new_tab=True).classes("text-sm")

    def add_actions(self, actions: ActionRegistry) -> None:
        TitsActions(self._request).add_to(actions)

    def _url(self, settings: dict[str, Any]) -> str:
        return self._base(settings) + "/websocket"

    @staticmethod
    def _base(settings: dict[str, Any]) -> str:
        return str(settings["url"]).strip().rstrip("/")

    def _more_lines(self) -> list[RequestSocket]:
        return [self._told]

    async def _request(self, kind: str, data: dict[str, Any] | None) -> dict[str, Any]:
        message: dict[str, Any] = {"apiName": "TITSPublicApi", "apiVersion": "1.0", "messageType": kind}
        if data is not None:
            message["data"] = data
        answer = await self._ask(message)
        data = answer.get("data") if isinstance(answer.get("data"), dict) else {}
        if "error" in str(answer.get("messageType") or "").casefold():
            raise RuntimeError(f"T.I.T.S.: {data.get('message') or answer.get('messageType')}")
        return data

    async def _event(self, message: dict[str, Any]) -> None:
        kind = EVENTS.get(str(message.get("messageType") or ""))
        if kind is None:
            return
        data = message.get("data") if isinstance(message.get("data"), dict) else {}
        event = {"trigger": str(data.get("triggerName") or ""), "trigger_id": str(data.get("triggerID") or "")}
        if kind == "tits.hit":
            event = {"item": str(data.get("itemName") or ""), "item_id": str(data.get("itemID") or ""), **event,
                     "strength": data.get("strength") or 0}
        self._events.publish(kind, event)
