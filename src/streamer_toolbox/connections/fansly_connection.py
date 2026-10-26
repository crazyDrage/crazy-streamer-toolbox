import json
import re
from collections.abc import Callable
from typing import Any

import websockets
from nicegui import ui

from streamer_toolbox.connections.fansly.fansly_news import FanslyNews
from streamer_toolbox.connections.websocket.line_connection import LineConnection
from streamer_toolbox.connections.websocket.request_socket import RequestSocket
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus

FANSLY_URL = "wss://chatws.fansly.com/?v=3"
JOIN = 46001
KEEP_ALIVE = (10.0, "p")  # the website sends a plain "p" every 10 s


class FanslyConnection(LineConnection):
    """Fansly, through the chat socket its website uses (Fansly has no public API; he OK'd this one for
    reading, 2026-10-17): it joins the chatroom whose id is typed on the tab and turns what comes in into
    `fansly.chat`, `fansly.tip` (also the toolbox's `tip`) and `fansly.sub` events (FanslyNews).

    Read only, and no login: the chatroom id is all it needs, nothing of his account is used. Sending chat would
    need a Fansly token and is left out on purpose. Built from what github.com/ZerGo0/fansly.streamerbot
    recorded; chat messages seen on his real chatroom (2026-10-17), tips and subs not yet. Off until switched
    on."""

    id = "fansly"
    title = "Fansly"
    icon = "forum"

    def __init__(self, settings: dict[str, Any], events: EventBus, url: str = FANSLY_URL,
                 connect: Callable[..., Any] = websockets.connect, retry_delay: float = 5.0,
                 beat: tuple[float, dict[str, Any] | str] = KEEP_ALIVE) -> None:
        self._events = events
        self._address = url
        self._news = FanslyNews()
        super().__init__({"chatroom": ""}, settings, connect, retry_delay, beat)

    def fields(self) -> list[SettingField]:
        return [SettingField("chatroom", "Your chatroom", hint="the chat's address or the number at its end "
                             "(Fansly → Streaming → the 3 dots next to the chat → Copy Chat Url)")]

    def add_gui_settings(self) -> None:
        ui.label("No login: the toolbox only reads your chatroom, like a viewer would. It can't write in it.") \
            .classes("text-sm opacity-80")
        ui.label("Fansly has no official API: this uses the chat connection of Fansly's own website, so it can "
                 "stop working when Fansly changes it. Chat messages were tried, tips and subs not yet. What comes in: "
                 "chat messages, tips (also as the toolbox's Tip trigger and Tip alert) and new subs.") \
            .classes("text-xs opacity-60")

    def _url(self, settings: dict[str, Any]) -> str:
        chatroom_id(settings)
        return self._address

    def _facts(self) -> tuple[tuple[str, str], ...]:
        return (("Chatroom", chatroom_id(self._settings)),)

    async def _opened(self, line: RequestSocket) -> None:
        await line.send({"t": JOIN, "d": json.dumps({"chatRoomId": chatroom_id(self._settings)})})

    async def _message(self, message: dict[str, Any]) -> None:
        for kind, data in self._news.news(message):
            self._events.publish(kind, data)


def chatroom_id(settings: dict[str, Any]) -> str:
    """The chatroom's number, from the number or the whole address; ValueError with words when there is none."""
    found = re.search(r"(\d{6,})/?\s*$", str(settings.get("chatroom") or ""))
    if found is None:
        raise ValueError("No chatroom yet: paste your Fansly chat's address (Copy Chat Url) or the number at its end")
    return found.group(1)
