import asyncio
import contextvars
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import httpx

from streamer_toolbox.connections.rumble.rumble_feed import HOST, RumbleFeed
from streamer_toolbox.connections.rumble.rumble_news import PLATFORM
from streamer_toolbox.core.connections.account_keys import AccountKeys, fit_name
from streamer_toolbox.core.connections.account_settings import ACCOUNT_DEFAULTS, AccountSettings
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.current_account import ACCOUNT
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import ACCOUNT_FIELD, MAIN_ACCOUNT_FIELD
from streamer_toolbox.core.interfaces.account_holder import AccountHolder

KEY_PAGE = "https://rumble.com/account/livestream-api"
FASTEST = 2.0  # seconds; Rumble doesn't say how often it may be asked


class RumbleConnection(ConnectionBase, AccountHolder):
    """Rumble, through its Live Stream API: follows, subscribers, gifted subs, and while a stream is live its
    chat messages and rants (paid messages). Each becomes a `rumble.…` event for flows; a rant also the
    toolbox's `tip` event (Tip trigger, Tip alert, widgets). Read only: Rumble's API has nothing to send with.
    Rumble has no live feed: the toolbox asks every few seconds, so a missed follow can't happen.

    The API is one address that holds the account's key. Several accounts (his plan docs/PLAN_multi_accounts.md,
    "for every streaming platform" 2026-11-06): each address is kept in config/secrets/rumble/<name>.txt (the
    name from Rumble's answer), never in toolbox.toml and never shown. Every account that listens (the main
    one, others he switches on) has its own feed, and its events say which account it was. Off until switched
    on."""

    id = "rumble"
    title = "Rumble"
    icon = "smart_display"

    def __init__(self, settings: dict[str, Any], keys: AccountKeys, events: EventBus,
                 transport: httpx.AsyncBaseTransport | None = None,
                 save_settings: Callable[[dict[str, Any]], None] | None = None) -> None:
        super().__init__({"seconds": "5", **ACCOUNT_DEFAULTS}, settings)
        self._keys = keys
        self._events = events
        self._transport = transport
        self._save_settings = save_settings
        self._accounts = AccountSettings(lambda: self._settings, self._save)
        self._listeners: dict[str, asyncio.Task] = {}
        self._states: dict[str, str] = {}  # account → "listening" or what went wrong

    def fields(self) -> list[SettingField]:
        return [SettingField("seconds", "Ask every (seconds)", hint="Rumble has no live feed: the toolbox asks "
                             f"again and again. Not faster than every {FASTEST:g} seconds.")]

    def add_gui_settings(self) -> None:
        from nicegui import ui

        from streamer_toolbox.gui.components.accounts_panel import AccountsPanel
        from streamer_toolbox.gui.components.outside_link import outside_link
        from streamer_toolbox.gui.components.rumble_account_adder import RumbleAccountAdder
        ui.label("Each account is its Live Stream API address (Rumble → account → Live Stream API). It holds the "
                 "account's key and can only read.").classes("text-sm opacity-80")
        outside_link("Open Rumble's page with the address", KEY_PAGE).classes("text-sm")
        ui.label("What comes in: follows, subscribers, gifted subs, and while you are live chat messages and "
                 "rants (a rant also as the toolbox's Tip trigger and Tip alert). Nothing can be sent to Rumble.") \
            .classes("text-xs opacity-60")
        AccountsPanel(self, RumbleAccountAdder(self)).build()

    async def start(self) -> None:
        await self.stop()
        main = self.main_account()
        try:
            self._address(main)
        except ValueError as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, str(e)))
            return
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING, "connecting"))
        loop = asyncio.get_running_loop()
        for name in self.listening_accounts():
            context = contextvars.copy_context()
            context.run(ACCOUNT.set, name)
            feed = RumbleFeed(self._address(name), self._handle, self._state, self._every(), self._transport)
            self._listeners[name] = loop.create_task(feed.run(), context=context)

    async def stop(self) -> None:
        for task in self._listeners.values():
            task.cancel()
        await asyncio.gather(*self._listeners.values(), return_exceptions=True)
        self._listeners, self._states = {}, {}
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Asks once with the main account's address: says whether Rumble takes it, and how many follow."""
        try:
            answer = await RumbleFeed(self._address(self.main_account()), self._handle,
                                      transport=self._transport).ask()
        except (ValueError, PermissionError, ConnectionError) as e:
            return ConnectionStatus(ConnectionState.ERROR, str(e))
        self._name_from(self.main_account(), answer)
        followers = answer.get("followers") if isinstance(answer.get("followers"), dict) else {}
        return ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("Followers", str(followers.get("num_followers_total", followers.get("num_followers", "?")))),))

    # ---- accounts ----

    def account_names(self) -> list[str]:
        return self._keys.names()

    def main_account(self) -> str:
        return self._keys.main_name()

    @property
    def multiple_accounts(self) -> bool:
        return self._accounts.multiple

    def is_bot(self, name: str) -> bool:
        return False  # read only: there is nothing a bot could do

    def listens(self, name: str) -> bool:
        return self._accounts.listens(name, self.main_account())

    def account_state(self, name: str) -> str:
        state = self._states.get(name, "")
        return "connected" if state == "listening" else state

    def where_kept(self, name: str) -> str:
        return f"config/secrets/rumble/{name}.txt"

    async def set_main_account(self, name: str) -> None:
        self._keys.set_main(name)
        await self._restart_if_on()

    def set_multiple_accounts(self, on: bool) -> None:
        self._accounts.set_multiple(on)

    async def set_listening(self, name: str, on: bool) -> None:
        self._accounts.set_listening(name, on)
        await self._restart_if_on()

    async def add_account(self, address: str) -> str:
        """Another account's Live Stream API address: asked once (Rumble must take it), kept under the name
        Rumble gives (its channel or user name). Its name."""
        address = check_address(address)
        answer = await RumbleFeed(address, self._handle, transport=self._transport).ask()
        name = answer_name(answer) or self._free_name()
        name = self._keys.save(name, address)
        await self._restart_if_on()
        return name

    async def remove_account(self, name: str) -> None:
        was_main = name == self.main_account()
        self._keys.remove(name)
        self._accounts.forget(name)
        if was_main or name in self._listeners:
            await self._restart_if_on()

    def listening_accounts(self) -> list[str]:
        return self._accounts.listening(self.main_account(), self.account_names())

    def account_choice(self) -> tuple[Callable[[], bool], Callable[[], list[str]]]:
        return (lambda: self.multiple_accounts), self.account_names

    # ---- internals ----

    def _every(self) -> float:
        try:
            return max(float(self._settings["seconds"]), FASTEST)
        except (TypeError, ValueError):
            return 5.0

    def _state(self, text: str) -> None:
        name = ACCOUNT.get() or self.main_account()
        self._states[name] = text
        if name != self.main_account():
            return
        if text == "listening":
            others = [n for n, s in self._states.items() if n != name and s == "listening"]
            self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (
                ("Account", name), *((("Other accounts", ", ".join(others)),) if others else ()),
                ("Feed", "events"))))
        else:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, text))

    async def _handle(self, kind: str, data: dict[str, Any]) -> None:
        extra = {ACCOUNT_FIELD: ACCOUNT.get() or self.main_account(), MAIN_ACCOUNT_FIELD: self.main_account()} \
            if kind.startswith(f"{PLATFORM}.") else {}  # the toolbox's own `tip` stays as it is
        self._events.publish(kind, {**data, **extra})

    def _address(self, name: str) -> str:
        text = self._keys.load(name) if name else ""
        if not text:
            raise ValueError("No address yet: Add account under Connections → Rumble with your Live Stream API "
                             "address")
        return check_address(text)

    def _name_from(self, name: str, answer: dict[str, Any]) -> None:
        """The account moved from the single file (named "rumble") gets the name Rumble gives it."""
        better = answer_name(answer)
        if better and name == MOVED and better not in self.account_names():
            self._keys.rename(name, better)

    def _free_name(self) -> str:
        names = set(self.account_names())
        return next(f"rumble_{n}" for n in range(2, 1000) if f"rumble_{n}" not in names)

    async def _restart_if_on(self) -> None:
        if self._settings["enabled"] and self._listeners:
            await self.stop()
            await self.start()

    def _save(self, values: dict[str, Any]) -> None:
        if self._save_settings is not None:
            self._save_settings(values)
        else:
            self.configure({**self._settings, **values})


MOVED = "rumble"  # the name the single address file gets when it moves (settings version 4)


def check_address(text: str) -> str:
    """The address as it may be used; ValueError (without the key) when it isn't Rumble's."""
    address = str(text or "").strip().splitlines()[0].strip() if str(text or "").strip() else ""
    parts = urlsplit(address)
    # the key must only ever go to Rumble: a pasted wrong address is refused before anything is sent
    if parts.scheme != "https" or (parts.hostname or "") not in (HOST, "www." + HOST):
        raise ValueError(f"The address must be an https://{HOST}/… address (your Live Stream API address)")
    return address


def answer_name(answer: dict[str, Any]) -> str:
    """The account's name in Rumble's answer: its channel's name, else the user's."""
    return fit_name(str(answer.get("channel_name") or answer.get("username") or ""))
