import asyncio
import secrets
import time
import webbrowser
from collections.abc import Callable
from typing import Any

import httpx
from nicegui import ui

from streamer_toolbox.connections.oauth.oauth_code_listener import OAuthCodeListener
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.connections.youtube.youtube_api import YouTubeApi
from streamer_toolbox.connections.youtube.youtube_api_error import YouTubeApiError
from streamer_toolbox.connections.youtube.youtube_auth import WRITE, YouTubeAuth
from streamer_toolbox.connections.youtube.youtube_chat import YouTubeChat
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.events.event_bus import EventBus

CONSOLE = "https://console.cloud.google.com/apis/credentials"
FASTEST = 3.0  # seconds between two asks of the chat


class YouTubeConnection(ConnectionBase):
    """The streamer's YouTube channel: while he is live, chat messages, Super Chats, Super Stickers, new
    members, member milestones and gifted memberships start flows (youtube/youtube_events.py has what each
    gives; a Super Chat or Sticker is also the toolbox's `tip`), plus stream online / offline and a Send chat
    message box.

    It needs a Google Cloud project of his own with the "YouTube Data API v3" switched on and an OAuth client
    (its Client ID and Secret go on the tab), like the Twitch app. Login only happens on Connect (a browser tab
    asks to allow the app); starting the toolbox never opens it. The login is kept in config/youtube_token.json
    (an OAuthToken, as Twitch's is) and renewed by itself. Reading is all it asks for, unless "May
    write in chat" is on: Google's only permission for sending a chat message is one that may manage the whole
    YouTube account, so that is his switch. Off until switched on."""

    id = "youtube"
    title = "YouTube"
    icon = "play_circle"

    def __init__(self, settings: dict[str, Any], tokens: OAuthTokenStore, events: EventBus,
                 transport: httpx.AsyncBaseTransport | None = None,
                 open_browser: Callable[[str], Any] = webbrowser.open, login_timeout: float = 180,
                 look: float = 60.0) -> None:
        super().__init__({"client_id": "", "client_secret": "",
                          "redirect_url": "http://localhost:17564", "seconds": "10", "may_write": "no"}, settings)
        self._tokens = tokens
        self._events = events
        self._transport = transport
        self._open_browser = open_browser
        self._login_timeout = login_timeout
        self._look = look
        self._token: OAuthToken | None = None
        self._chat: YouTubeChat | None = None
        self._listener: asyncio.Task | None = None
        self._listening = "not yet"
        self._refresh_lock = asyncio.Lock()

    def fields(self) -> list[SettingField]:
        return [SettingField("client_id", "Client ID", hint="Google Cloud console → your project → Credentials"),
                SettingField("client_secret", "Client Secret", secret=True),
                SettingField("redirect_url", "Redirect URL",
                             hint="must be one of the OAuth client's redirect URIs (default: http://localhost:17564)"),
                SettingField("seconds", "Ask the chat every (seconds)",
                             hint="each ask costs quota (10 000 points a day): 10 seconds lasts about 5 hours of "
                                  "stream, 5 seconds half of that"),
                SettingField("may_write", "May write in chat (yes / no)",
                             hint="yes asks Google for a permission that may manage your whole YouTube account "
                                  "(there is no smaller one for sending chat). Press Connect again after changing")]

    def add_gui_settings(self) -> None:
        ui.label("Needs a Google Cloud project of your own: switch on \"YouTube Data API v3\", make an OAuth "
                 "client (type Web application, redirect URI as above), put its Client ID and Secret here, press "
                 "Connect.").classes("text-sm opacity-80")
        ui.link("Open the Google Cloud console", CONSOLE, new_tab=True).classes("text-sm")
        ui.label("What comes in while you are live: chat messages, Super Chats and Super Stickers (both also as "
                 "the toolbox's Tip trigger and Tip alert), new members, member milestones, gifted memberships. "
                 "YouTube has no event for a new subscriber.").classes("text-xs opacity-60")

    # ---- Connection ----

    async def start(self) -> None:
        await self.stop()
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING))
        try:
            self._token = await self._usable_token(self._settings, self._tokens.load())
        except Exception as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))
            return
        self._chat = YouTubeChat(self._api(), self._event, self._chat_state, self._every(), self._look)
        self._listener = asyncio.get_running_loop().create_task(self._run(self._chat))
        self._show_connected()

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            await asyncio.gather(self._listener, return_exceptions=True)
        self._listener, self._chat, self._token = None, None, None
        self._listening = "not yet"
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Uses the saved login if it still works, else logs in through the browser."""
        if not settings.get("client_id") or not settings.get("client_secret"):
            return ConnectionStatus(ConnectionState.ERROR, "Client ID and Client Secret are needed")
        try:
            try:
                token = await self._usable_token(settings, self._tokens.load())
            except PermissionError:
                token = await self._login(settings)
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Channel", token.login),))

    # ---- what actions use ----

    async def send_chat(self, message: str) -> None:
        """Writes in the live chat as him. Needs "May write in chat" and a stream that is live."""
        token = self._need_token()
        if WRITE not in token.scopes:
            raise PermissionError("YouTube: writing in chat isn't allowed yet. Set \"May write in chat\" to yes "
                                  "under Connections → YouTube and press Connect once")
        if self._chat is None or self._chat.chat is None:
            raise NotConnectedError("YouTube: no live stream right now, so there is no chat to write in")
        await self._api().send_chat(self._chat.chat["chat"], str(message))

    def add_actions(self, actions: ActionRegistry) -> None:
        actions.add("youtube.send_chat", self.send_chat, "Writes in your YouTube live chat as you (only while "
                    "live, and only with \"May write in chat\" switched on)", "Send chat message", group="Chat")

    # ---- internals ----

    async def _run(self, chat: YouTubeChat) -> None:
        try:
            await chat.run()
        except PermissionError as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))

    async def _usable_token(self, settings: dict[str, Any], token: OAuthToken | None) -> OAuthToken:
        """The saved login, renewed if needed; PermissionError when there is none that works."""
        if token is None:
            raise PermissionError("Not logged in yet: press Connect and allow the app in the browser")
        if to_bool(settings.get("may_write")) and WRITE not in token.scopes:
            raise PermissionError("The saved login may only read: press Connect to allow writing in chat")
        if token.expires_soon():
            token = await self._renew(self._auth(settings), token)
        return token

    async def _renew(self, auth: YouTubeAuth, token: OAuthToken) -> OAuthToken:
        try:
            answer = await auth.refresh(token.refresh_token)
        except YouTubeApiError as e:
            raise PermissionError(f"The YouTube login expired ({e}): press Connect to log in again") from e
        renewed = _token(answer, token)
        self._tokens.save(renewed)
        return renewed

    async def _login(self, settings: dict[str, Any]) -> OAuthToken:
        auth = self._auth(settings)
        port = httpx.URL(auth.redirect_uri).port or 80
        listener = OAuthCodeListener("localhost", port, "YouTube")
        state = secrets.token_urlsafe(16)
        try:
            await listener.start(state)
        except OSError as e:
            raise ConnectionError(f"port {port} is busy (another tool logging in?): {e}") from e
        url = auth.authorize_url(state, write=to_bool(settings.get("may_write")))
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING,
                                          f"Allow the app in the browser tab that opened on the PC. No tab? {url}"))
        self._open_browser(url)
        code = await listener.wait(self._login_timeout)
        token = _token(await auth.exchange(code))

        async def fresh(renew: bool = False) -> str:
            return token.access_token

        channel = await YouTubeApi(fresh, self._transport).channel()
        token = OAuthToken(token.access_token, token.refresh_token, token.expires_at, token.scopes,
                            channel["id"], channel["title"])
        self._tokens.save(token)
        return token

    async def _access_token(self, renew: bool = False) -> str:
        self._need_token()
        async with self._refresh_lock:
            token = self._token
            if renew or token.expires_soon():
                self._token = token = await self._renew(self._auth(self._settings), token)
        return token.access_token

    def _need_token(self) -> OAuthToken:
        if not self._settings["enabled"]:
            raise NotConnectedError("YouTube is switched off under Connections → YouTube")
        if self._token is None:
            raise NotConnectedError(f"YouTube: {self.status.detail or 'not connected'}")
        return self._token

    def _auth(self, settings: dict[str, Any]) -> YouTubeAuth:
        return YouTubeAuth(settings["client_id"], settings["client_secret"], settings["redirect_url"],
                           self._transport)

    def _api(self) -> YouTubeApi:
        return YouTubeApi(self._access_token, self._transport)

    def _every(self) -> float:
        try:
            return max(float(self._settings["seconds"]), FASTEST)
        except (TypeError, ValueError):
            return 10.0

    async def _event(self, kind: str, data: dict[str, Any]) -> None:
        self._events.publish(kind, data)

    def _chat_state(self, text: str) -> None:
        self._listening = text
        if self._token is not None:
            if text.startswith(("not listening", "today's")):
                self._set_status(ConnectionStatus(ConnectionState.ERROR, text))
            else:
                self._show_connected()

    def _show_connected(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("Channel", self._token.login), ("Chat", self._listening),
            ("May write", "yes" if WRITE in self._token.scopes else "no"))))


def _token(answer: dict[str, Any], old: OAuthToken | None = None) -> OAuthToken:
    """From Google's token answer: its scopes are one text with spaces, and a refresh brings no new refresh
    token (the old one, and who it is, stay)."""
    scopes = tuple(str(answer.get("scope") or "").split()) or (old.scopes if old else ())
    return OAuthToken(answer["access_token"], answer.get("refresh_token") or (old.refresh_token if old else ""),
                       time.time() + float(answer.get("expires_in", 3600)), scopes,
                       old.user_id if old else "", old.login if old else "")


def _reason(e: Exception) -> str:
    if isinstance(e, TimeoutError):
        return "Nobody allowed the app in the browser in time. Press Connect to try again."
    if isinstance(e, (PermissionError, YouTubeApiError, ConnectionError)):
        return str(e)
    if isinstance(e, httpx.HTTPError):
        return f"can't reach YouTube: {type(e).__name__}"
    return str(e) or type(e).__name__
