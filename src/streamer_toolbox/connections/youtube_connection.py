import asyncio
import contextvars
import secrets
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from streamer_toolbox.connections.oauth.account_tokens import AccountTokens
from streamer_toolbox.connections.oauth.oauth_code_listener import OAuthCodeListener
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.youtube.boxes.send_chat_message import SendChatMessage
from streamer_toolbox.connections.youtube.youtube_api import YouTubeApi
from streamer_toolbox.connections.youtube.youtube_api_error import YouTubeApiError
from streamer_toolbox.connections.youtube.youtube_auth import WRITE, YouTubeAuth
from streamer_toolbox.connections.youtube.youtube_chat import YouTubeChat
from streamer_toolbox.connections.youtube.youtube_events import FOLLOW, PLATFORM
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.account_keys import fit_name
from streamer_toolbox.core.connections.account_settings import ACCOUNT_DEFAULTS, AccountSettings
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.current_account import ACCOUNT
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import ACCOUNT_FIELD, MAIN_ACCOUNT_FIELD
from streamer_toolbox.core.followers.follower_check import FollowerCheck
from streamer_toolbox.core.followers.seen_followers import FOLLOWERS, SeenFollowers
from streamer_toolbox.core.interfaces.account_holder import AccountHolder

CONSOLE = "https://console.cloud.google.com/apis/credentials"
FASTEST = 3.0  # seconds between two asks of the chat


class YouTubeConnection(ConnectionBase, AccountHolder):
    """The streamer's YouTube channel: while he is live, chat messages, Super Chats, Super Stickers, new
    members, member milestones and gifted memberships start flows (youtube/youtube_events.py has what each
    gives; a Super Chat or Sticker is also the toolbox's `tip`), new subscribers come from the subscriber check,
    plus stream online / offline and a Send chat message box.

    It needs a Google Cloud project of his own with the "YouTube Data API v3" switched on and an OAuth client
    (its Client ID and Secret go on the tab). Login only happens on Connect or Add account (a browser tab on this
    PC asks to allow the app); starting the toolbox never opens it. Reading is all it asks for, unless "May
    write in chat" is on: Google's only permission for sending a chat message is one that may manage the whole
    YouTube account, so that is his switch (a bot account always asks for it: writing is what it is for).

    Several accounts (his plan docs/PLAN_multi_accounts.md, "for every streaming platform" 2026-11-06): each
    login is kept in config/secrets/youtube/<name>.json, the name from the channel's handle. Every call uses the
    account of the work that runs (current_account.ACCOUNT), the main one when none is set; each account that
    listens has its own chat listener and subscriber check, and its events say which account it was. A bot
    account writes in the main account's live chat. Off until switched on."""

    id = "youtube"
    title = "YouTube"
    icon = "play_circle"

    def __init__(self, settings: dict[str, Any], tokens: AccountTokens, events: EventBus,
                 transport: httpx.AsyncBaseTransport | None = None,
                 open_browser: Callable[[str], Any] = webbrowser.open, login_timeout: float = 180,
                 look: float = 60.0, folder: Path | None = None,
                 save_settings: Callable[[dict[str, Any]], None] | None = None) -> None:
        super().__init__({"client_id": "", "client_secret": "", "redirect_url": "http://localhost:17564",
                          "seconds": "10", "may_write": "no", "follower_check": "60", **ACCOUNT_DEFAULTS}, settings)
        self._tokens = tokens
        self._events = events
        self._transport = transport
        self._open_browser = open_browser
        self._login_timeout = login_timeout
        self._look = look
        self._folder = folder  # the settings folder: followers/youtube_<account>.json
        self._save_settings = save_settings
        self._accounts = AccountSettings(lambda: self._settings, self._save)
        self._logins: dict[str, OAuthToken] = {}  # account → its working login (checked at start)
        self._problems: dict[str, str] = {}  # account → why it doesn't work
        self._chats: dict[str, YouTubeChat] = {}  # account → its chat listener
        self._chat_states: dict[str, str] = {}
        self._tasks: list[asyncio.Task] = []
        self._refresh_locks: dict[str, asyncio.Lock] = {}
        self._login_lock = asyncio.Lock()  # one browser login at a time (one port)

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
                                  "(there is no smaller one for sending chat). Press Connect again after changing"),
                SettingField("follower_check", "Check for new subscribers every (seconds)",
                             hint="YouTube has no event for them, so the toolbox asks; each ask costs 1 quota point "
                                  "(every 60 seconds: 1 440 a day). Only public subscriptions. 0 = off")]

    def default_flows(self) -> Path:
        return Path(__file__).parent / "youtube" / "default_flows.flows.toml"

    def add_gui_settings(self) -> None:
        from nicegui import ui

        from streamer_toolbox.gui.components.accounts_panel import AccountsPanel
        from streamer_toolbox.gui.components.outside_link import outside_link
        from streamer_toolbox.gui.components.youtube_account_adder import YouTubeAccountAdder
        ui.label("Needs a Google Cloud project of your own: switch on \"YouTube Data API v3\", make an OAuth "
                 "client (type Web application, redirect URI as above), put its Client ID and Secret here, press "
                 "Connect.").classes("text-sm opacity-80")
        outside_link("Open the Google Cloud console", CONSOLE).classes("text-sm")
        ui.label("What comes in while you are live: chat messages, Super Chats and Super Stickers (both also as "
                 "the toolbox's Tip trigger and Tip alert), new members, member milestones, gifted memberships. "
                 "New subscribers come from the subscriber check (YouTube has no event for them).") \
            .classes("text-xs opacity-60")
        AccountsPanel(self, YouTubeAccountAdder(self)).build()

    # ---- Connection ----

    async def start(self) -> None:
        await self.stop()
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING))
        main = self.main_account()
        try:
            token = await self._usable_token(main, self._tokens.load_account(main) if main else None)
            self._logins[self._saved_as(token, main)] = token
        except Exception as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))
            return
        for name in self.account_names():  # the others: one that doesn't work only shows on the tab
            if name not in self._logins:
                await self._check_account(name)
        loop = asyncio.get_running_loop()
        for name in self.listening_accounts():
            context = contextvars.copy_context()
            context.run(ACCOUNT.set, name)
            chat = YouTubeChat(self._api(), self._event, self._chat_state, self._every(), self._look)
            self._chats[name] = chat
            self._tasks.append(loop.create_task(self._run(chat), context=context))
            path = self._folder / FOLLOWERS / f"{PLATFORM}_{name}.json" if self._folder else None
            check = FollowerCheck(self._api().newest_subscribers, self._new_subscriber, SeenFollowers(path),
                                  self._follower_seconds)
            self._tasks.append(loop.create_task(check.run(), context=context))
        self._show_connected()

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks, self._chats, self._chat_states, self._logins, self._problems = [], {}, {}, {}, {}
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Uses the main account's saved login if it still works, else logs in through the browser (the account
        that logs in is the main one from then on)."""
        if not settings.get("client_id") or not settings.get("client_secret"):
            return ConnectionStatus(ConnectionState.ERROR, "Client ID and Client Secret are needed")
        try:
            main = self.main_account()
            try:
                token = await self._usable_token(main, self._tokens.load_account(main) if main else None, settings)
            except PermissionError:
                token = await self._login(settings)
                self._tokens.save(token)  # the account that logged in is the main one
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Channel", token.login),))

    # ---- accounts (the tab's account list, his plan docs/PLAN_multi_accounts.md) ----

    def account_choice(self) -> tuple[Callable[[], bool], Callable[[], list[str]]]:
        return (lambda: self.multiple_accounts), self.account_names

    def account_names(self) -> list[str]:
        return self._tokens.names()

    def main_account(self) -> str:
        return self._tokens.main_name()

    @property
    def multiple_accounts(self) -> bool:
        return self._accounts.multiple

    def is_bot(self, name: str) -> bool:
        return self._accounts.is_bot(name)

    def has_bots(self) -> bool:
        return True

    def listens(self, name: str) -> bool:
        return self._accounts.listens(name, self.main_account())

    def account_state(self, name: str) -> str:
        if name in self._logins:
            return self._problems.get(name) or "connected"
        return self._problems.get(name, "")

    def where_kept(self, name: str) -> str:
        return f"config/secrets/youtube/{name}.json"

    async def set_main_account(self, name: str) -> None:
        self._tokens.set_main(name)
        await self._restart_if_on()

    def set_multiple_accounts(self, on: bool) -> None:
        self._accounts.set_multiple(on)

    async def set_listening(self, name: str, on: bool) -> None:
        self._accounts.set_listening(name, on)
        await self._restart_if_on()

    async def add_account(self, bot: bool, show: Callable[[str], None]) -> str:
        """Logs in one more account (or one again) in a browser on this PC: Google asks which of its accounts
        (show(link) gets the page too, for another browser on this PC). A bot account asks to write in chat
        (that's what it's for); a channel account like Connect. Its name; it is in the list from then on."""
        token = await self._login(self._settings, write=bot or None, choose=True, show=show)
        name = self._tokens.save_account(token)
        self._accounts.set_bot(name, bot)
        if self._logins:  # running: usable right away
            await self._check_account(name)
            self._show_connected()
        return name

    async def remove_account(self, name: str) -> None:
        was_main = name == self.main_account()
        self._tokens.remove(name)
        self._logins.pop(name, None)
        self._problems.pop(name, None)
        self._accounts.forget(name)
        if was_main:
            await self._restart_if_on()
        elif self._logins:
            self._show_connected()

    def listening_accounts(self) -> list[str]:
        return self._accounts.listening(self.main_account(), self._logins)

    # ---- what actions use ----

    async def send_chat(self, message: str) -> None:
        """Writes in the live chat of the account's channel (a bot account: the main account's) as that
        account. Needs "May write in chat" (a bot account always has it) and a stream that is live."""
        token = self._need_token()
        if WRITE not in token.scopes:
            raise PermissionError("YouTube: writing in chat isn't allowed yet. Set \"May write in chat\" to yes "
                                  "under Connections → YouTube and press Connect once")
        await self._api().send_chat(await self._live_chat(), str(message))

    def add_actions(self, actions: ActionRegistry) -> None:
        for box in (SendChatMessage(self),):
            actions.add_box(box, "youtube")

    # ---- internals ----

    async def _live_chat(self) -> str:
        """The live chat the account writes in: its channel's, a bot account's: the main account's."""
        name = self._account()
        channel = self.main_account() if self.is_bot(name) else name
        listener = self._chats.get(channel)
        if listener is not None and listener.chat is not None:
            return listener.chat["chat"]
        if listener is None and channel in self._logins:  # an account that doesn't listen: ask once
            mark = ACCOUNT.set(channel)
            try:
                found = await self._api().live_chat()
            finally:
                ACCOUNT.reset(mark)
            if found is not None:
                return found["chat"]
        raise NotConnectedError(f"YouTube: no live stream on {channel} right now, so there is no chat to write in")

    async def _run(self, chat: YouTubeChat) -> None:
        try:
            await chat.run()
        except PermissionError as e:
            self._chat_state(str(e), error=True)

    async def _check_account(self, name: str) -> None:
        try:
            token = await self._usable_token(name, self._tokens.load_account(name))
            self._logins[self._saved_as(token, name)] = token
            self._problems.pop(name, None)
        except Exception as e:
            self._logins.pop(name, None)
            self._problems[name] = _reason(e)

    async def _usable_token(self, name: str, token: OAuthToken | None,
                            settings: dict[str, Any] | None = None) -> OAuthToken:
        """An account's saved login, renewed if needed; PermissionError when there is none that works."""
        settings = settings or self._settings
        if token is None:
            raise PermissionError("Not logged in yet: press Connect and allow the app in the browser")
        if self.is_bot(name) and WRITE not in token.scopes:
            raise PermissionError("This bot account may not write in chat: Log in again")
        if (name == self.main_account() and to_bool(settings.get("may_write"))
                and WRITE not in token.scopes):
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
        self._tokens.save_account(renewed)
        return renewed

    async def _login(self, settings: dict[str, Any], write: bool | None = None, choose: bool = False,
                     show: Callable[[str], None] | None = None) -> OAuthToken:
        """A login in the browser of this PC (Google sends the answer to the redirect URL here). The token's
        login is the account's name (account_name)."""
        async with self._login_lock:
            auth = self._auth(settings)
            port = httpx.URL(auth.redirect_uri).port or 80
            listener = OAuthCodeListener("localhost", port, "YouTube")
            state = secrets.token_urlsafe(16)
            try:
                await listener.start(state)
            except OSError as e:
                raise ConnectionError(f"port {port} is busy (another tool logging in?): {e}") from e
            url = auth.authorize_url(state, write=to_bool(settings.get("may_write")) if write is None else write,
                                     choose=choose)
            if show is not None:  # Add account: the tab shows the link, the status stays as it is
                show(url)
            else:
                self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "Allow the app in the browser tab "
                                                  f"that opened on the PC. No tab? {url}"))
            self._open_browser(url)
            code = await listener.wait(self._login_timeout)
        token = _token(await auth.exchange(code))

        async def fresh(renew: bool = False) -> str:
            return token.access_token

        channel = await YouTubeApi(fresh, self._transport).channel()
        return OAuthToken(token.access_token, token.refresh_token, token.expires_at, token.scopes,
                          channel["id"], account_name(channel))

    async def _access_token(self, renew: bool = False) -> str:
        name = self._account()
        self._need_token()
        async with self._refresh_locks.setdefault(name, asyncio.Lock()):
            token = self._logins[name]
            if renew or token.expires_soon():
                self._logins[name] = token = await self._renew(self._auth(self._settings), token)
        return token.access_token

    def _account(self) -> str:
        """The account the running work is for: its Account field / its own listener, else the main one."""
        return ACCOUNT.get() or self.main_account()

    def _need_token(self) -> OAuthToken:
        if not self._settings["enabled"]:
            raise NotConnectedError("YouTube is switched off under Connections → YouTube")
        name = self._account()
        token = self._logins.get(name)
        if token is not None:
            return token
        if not self._logins:
            raise NotConnectedError(f"YouTube: {self.status.detail or 'not connected'}")
        if name not in self.account_names():
            raise NotConnectedError(f"YouTube: there is no account {name!r} (any more): Connections → YouTube")
        raise NotConnectedError(f"YouTube account {name}: {self._problems.get(name) or 'not logged in'}")

    def _saved_as(self, token: OAuthToken, name: str) -> str:
        """The account's name after its check: an old login whose name doesn't fit is kept under its own."""
        return name if fit_name(token.login) == name else self._tokens.save_account(token, name)

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

    def _follower_seconds(self) -> float:
        try:
            return float(self._settings.get("follower_check") or 0)
        except (TypeError, ValueError):
            return 60.0

    async def _event(self, kind: str, data: dict[str, Any]) -> None:
        self._publish(kind, data)

    def _new_subscriber(self, follower: dict[str, Any]) -> None:
        self._publish(FOLLOW, {**follower, "platform": PLATFORM})

    def _publish(self, kind: str, data: dict[str, Any]) -> None:
        extra = {ACCOUNT_FIELD: self._account(), MAIN_ACCOUNT_FIELD: self.main_account()} \
            if kind.startswith(f"{PLATFORM}.") else {}  # the toolbox's own `tip` stays as it is
        self._events.publish(kind, {**data, **extra})

    def _chat_state(self, text: str, error: bool = False) -> None:
        name = self._account()
        self._chat_states[name] = text
        if name != self.main_account():  # another account's listener: its own line on the tab
            self._problems[name] = "" if text in ("listening", "waiting for a stream") else f"chat: {text}"
            return
        if self._logins:
            if error or text.startswith(("not listening", "today's")):
                self._set_status(ConnectionStatus(ConnectionState.ERROR, text))
            else:
                self._show_connected()

    def _show_connected(self) -> None:
        main = self._logins.get(self.main_account())
        if main is None:
            return
        others = [name for name in self._logins if name != self.main_account()]
        more = (("Other accounts", ", ".join(others)),) if others else ()
        self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("Channel", main.login), *more, ("Chat", self._chat_states.get(self.main_account(), "not yet")),
            ("May write", "yes" if WRITE in main.scopes else "no"))))

    async def _restart_if_on(self) -> None:
        if self._settings["enabled"] and self._logins:
            await self.stop()
            await self.start()

    def _save(self, values: dict[str, Any]) -> None:
        if self._save_settings is not None:
            self._save_settings(values)
        else:
            self.configure({**self._settings, **values})


def account_name(channel: dict[str, str]) -> str:
    """A YouTube account's name in the toolbox (a file name, the Account field): the handle without its @, else
    the title, else the channel id; letters, digits and _ only."""
    for text in (channel.get("handle", "").lstrip("@"), channel.get("title", ""), channel.get("id", "")):
        if fit_name(text):
            return fit_name(text)
    return "youtube"


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
