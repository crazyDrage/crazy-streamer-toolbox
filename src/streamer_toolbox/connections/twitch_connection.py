import asyncio
import contextvars
import logging
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import websockets

from streamer_toolbox.connections.twitch.boxes.create_reward import CreateReward
from streamer_toolbox.connections.twitch.boxes.finish_refund_redeem import FinishRefundRedeem
from streamer_toolbox.connections.twitch.boxes.get_rewards import GetRewards
from streamer_toolbox.connections.twitch.boxes.pause_reward import PauseReward
from streamer_toolbox.connections.twitch.boxes.reward_on_off import RewardOnOff
from streamer_toolbox.connections.twitch.boxes.send_chat_message import SendChatMessage
from streamer_toolbox.connections.twitch.boxes.stream_marker import StreamMarker
from streamer_toolbox.connections.twitch.eventsub_client import EVENTSUB_URL, EventSubClient
from streamer_toolbox.connections.twitch.eventsub_events import subscriptions, to_event
from streamer_toolbox.connections.twitch.twitch_api import TwitchApi
from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.connections.twitch.twitch_auth import (BOT_NEEDS, BOT_SCOPES, BUILT_IN_CLIENT_ID, EXTRA_SCOPES,
                                                             SCOPES, TwitchAuth)
from streamer_toolbox.connections.twitch.twitch_channel_actions import TwitchChannelActions
from streamer_toolbox.connections.twitch.twitch_clip_actions import TwitchClipActions
from streamer_toolbox.connections.twitch.twitch_clip_downloader import (REPO, TwitchClipDownloader, program_name,
                                                                        release_file)
from streamer_toolbox.connections.twitch.twitch_clip_files import TwitchClipFiles
from streamer_toolbox.connections.twitch.twitch_clip_question import TwitchClipQuestion
from streamer_toolbox.connections.twitch.twitch_stream_actions import TwitchStreamActions
from streamer_toolbox.connections.twitch.twitch_viewer_actions import TwitchViewerActions
from streamer_toolbox.connections.twitch.twitch_reward import TwitchReward
from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.connections.oauth.account_tokens import AccountTokens
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.account_settings import ACCOUNT_DEFAULTS, AccountSettings
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.current_account import ACCOUNT
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.events.event_fields import ACCOUNT_FIELD, MAIN_ACCOUNT_FIELD
from streamer_toolbox.core.system.github_program import GithubProgram
from streamer_toolbox.core.flows.flow_trigger import REWARDS
from streamer_toolbox.core.followers.follower_check import FollowerCheck
from streamer_toolbox.core.followers.seen_followers import FOLLOWERS, SeenFollowers
from streamer_toolbox.core.interfaces.account_holder import AccountHolder
from streamer_toolbox.core.interfaces.reward_manager import RewardManager

REDEEM = "twitch.redeem"
CHAT = "twitch.chat"
FOLLOW = "twitch.follow"
log = logging.getLogger(__name__)
PLATFORM = "twitch"  # every Twitch event says so (a flow on the common events tells them apart by it)
STREAM_EVENTS = ("twitch.online", "twitch.offline")  # these also say the stream's title and category


class TwitchConnection(ConnectionBase, RewardManager, AccountHolder):
    """The streamer's Twitch account: redeems, chat, follows, subs, gifts, cheers, raids, stream online / offline
    and ad breaks start flows (twitch/eventsub_events.py has what each gives), plus chat, reward and marker
    actions.

    Login only happens on Connect; starting the toolbox never opens it. It uses the toolbox's own Twitch app:
    Twitch's page opens with a short code to confirm, no setup (an app of his own is gone since 2026-11-05: his
    "we don't need a custom one anymore"). Each account's login is kept in config/secrets/twitch/<login>.json
    (AccountTokens) and renewed by itself.

    Several accounts (his plan docs/PLAN_multi_accounts.md): Connect logs in the main account; the tab adds
    more (a link to open where that account is logged in). Every call uses the account of the work that runs
    (current_account.ACCOUNT: a box's Account field, an account's own events), the main one when none is set.
    Settings: main_account, multiple_accounts (boxes and triggers get an Account field), bot_accounts (logged in
    with BOT_SCOPES only), listen (other accounts whose own channel's events come in too).
    """

    id = "twitch"
    title = "Twitch"
    icon = "live_tv"

    def __init__(self, settings: dict[str, Any], tokens: AccountTokens, events: EventBus,
                 transport: httpx.AsyncBaseTransport | None = None, ws_connect: Callable[..., Any] = websockets.connect,
                 eventsub_url: str = EVENTSUB_URL, open_browser: Callable[[str], Any] = webbrowser.open,
                 login_timeout: float = 180, code_wait: float = 1.0, folder: Path | None = None,
                 raw: Callable[[str, dict[str, Any]], None] | None = None,
                 save_settings: Callable[[dict[str, Any]], None] | None = None) -> None:
        super().__init__({**ACCOUNT_DEFAULTS, "follower_check": "60"}, settings)
        self._tokens = tokens
        self._accounts = AccountSettings(lambda: self._settings, self._save)
        self._save_settings = save_settings  # keeps a changed setting (toolbox.toml [twitch]) and configures
        self._folder = folder  # the settings folder: where the clip downloader and its clips are kept
        self._events = events
        self._raw = raw  # gets (event name, Twitch's own message) right before the event goes out
        self._transport = transport
        self._ws_connect = ws_connect
        self._eventsub_url = eventsub_url
        self._open_browser = open_browser
        self._login_timeout = login_timeout
        self._code_wait = code_wait  # the shortest pause between two asks "did he confirm the code?"
        self._logins: dict[str, OAuthToken] = {}  # account → its working login (checked at start)
        self._problems: dict[str, str] = {}  # account → why its login doesn't work
        self._eventsubs: dict[str, asyncio.Task] = {}  # account → its event listener
        self._follower_checks: dict[str, asyncio.Task] = {}  # account → its follower check (the failsafe)
        self._seen: dict[str, SeenFollowers] = {}  # account → the followers it has had
        self._announce: asyncio.Task | None = None  # keeps the reward list task alive
        self._listening = "not yet"
        self._missing_events: list[str] = []
        self._refresh_locks: dict[str, asyncio.Lock] = {}

    def fields(self) -> list[SettingField]:  # nothing else to type: Connect logs in with the toolbox's own app
        return [SettingField("follower_check", "Check for new followers every (seconds)",
                             hint="a failsafe for follows Twitch's live event misses; each follow still comes "
                                  "only once. 0 = off")]

    def add_gui_settings(self) -> None:
        from streamer_toolbox.gui.components.accounts_panel import AccountsPanel
        from streamer_toolbox.gui.components.twitch_account_adder import TwitchAccountAdder
        AccountsPanel(self, TwitchAccountAdder(self)).build()

    # ---- Connection ----

    async def start(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING))
        self._logins, self._problems = {}, {}
        main = self.main_account()
        try:
            token = await self._usable_token(main, self._tokens.load_account(main) if main else None)
            self._logins[_saved_as(token, main)] = token
        except Exception as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))
            return
        for name in self.account_names():  # the others: one that doesn't work only shows on the tab
            if name != main:
                await self._check_account(name)
        self._start_eventsub()
        self._start_follower_checks()
        self._show_connected()
        self._announce = asyncio.get_running_loop().create_task(self._announce_rewards())

    async def _announce_rewards(self) -> None:
        """Tells the flows the rewards as they are now (id + title), so triggers of a renamed reward update."""
        try:
            rewards = await self._api().rewards(self._need_token().user_id)
        except Exception as e:  # only names on screen depend on it
            log.info("Twitch: reward list not read (%s)", e)
            return
        self._events.publish(REWARDS, {"rewards": [{"id": r["id"], "title": r["title"]} for r in rewards]})

    async def stop(self) -> None:
        tasks = [*self._eventsubs.values(), *self._follower_checks.values()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._eventsubs, self._follower_checks = {}, {}
        self._listening = "not yet"
        self._logins = {}
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Uses the main account's saved login if it still works for this app, else logs in through the browser
        (the account that logs in is the main one from then on). A login that works but is from before a
        permission was added (EXTRA_SCOPES) logs in again too, so Connect brings the new permissions; if that
        isn't finished, the saved login stays as it is."""
        try:
            try:
                main = self.main_account()
                token = await self._usable_token(main, self._tokens.load_account(main) if main else None)
            except PermissionError:
                token = await self._login()
            else:
                if set(EXTRA_SCOPES) - set(token.scopes):
                    token = await self._login()
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Account", token.login),))

    # ---- accounts (the tab's account list, his plan docs/PLAN_multi_accounts.md) ----

    def account_choice(self) -> tuple[Callable[[], bool], Callable[[], list[str]]]:
        return (lambda: self.multiple_accounts), self.account_names

    def account_names(self) -> list[str]:
        """Every account with a login, A to Z."""
        return self._tokens.names()

    def main_account(self) -> str:
        return self._tokens.main_name()

    @property
    def multiple_accounts(self) -> bool:
        """His switch: boxes and triggers get an Account field."""
        return self._accounts.multiple

    def is_bot(self, name: str) -> bool:
        return self._accounts.is_bot(name)

    def has_bots(self) -> bool:
        return True

    def listens(self, name: str) -> bool:
        """Its own channel's events come in: always for the main account, for another when he switched it on."""
        return self._accounts.listens(name, self.main_account())

    def where_kept(self, name: str) -> str:
        return f"config/secrets/twitch/{name}.json"

    def account_state(self, name: str) -> str:
        """One line for the account list: "connected", why not, or "" while the connection is off."""
        if name in self._logins:
            return self._problems.get(name) or "connected"  # its own events may have trouble
        return self._problems.get(name, "")

    async def set_main_account(self, name: str) -> None:
        """His drop-down. A running connection starts again on the new main account (its events, its status)."""
        self._tokens.set_main(name)
        await self._restart_if_on()

    def set_multiple_accounts(self, on: bool) -> None:
        self._accounts.set_multiple(on)

    async def set_listening(self, name: str, on: bool) -> None:
        """Another account's own channel: its events come in too (his answer 120, off by default)."""
        self._accounts.set_listening(name, on)
        await self._restart_if_on()

    async def add_account(self, bot: bool, show: Callable[[str, str], None], wait: float = 1800) -> str:
        """Logs in one more account (or one again): show(link, code) gets Twitch's page and the code to confirm
        there, in any browser where that account is logged in (nothing opens on this PC). A bot account asks for
        BOT_SCOPES only (his answer 119 c). Its name; it is in the list from then on."""
        scopes = BOT_SCOPES if bot else SCOPES + EXTRA_SCOPES
        token = await self._login_with_code(self._auth(), scopes, show, wait)
        name = self._tokens.save_account(token)
        self._accounts.set_bot(name, bot)
        if self._logins:  # running: usable right away
            await self._check_account(name)
            self._show_connected()
        return name

    async def remove_account(self, name: str) -> None:
        """Forgets an account's login (its file). Boxes and triggers that name it say it's missing."""
        was_main = name == self.main_account()
        self._tokens.remove(name)
        self._logins.pop(name, None)
        self._problems.pop(name, None)
        self._accounts.forget(name)
        if was_main:
            await self._restart_if_on()
        elif self._logins:
            self._show_connected()

    async def _check_account(self, name: str) -> None:
        try:
            token = await self._usable_token(name, self._tokens.load_account(name))
            self._logins[_saved_as(token, name)] = token
            self._problems.pop(name, None)
        except Exception as e:
            self._logins.pop(name, None)
            self._problems[name] = _reason(e)

    async def _restart_if_on(self) -> None:
        if self._settings["enabled"] and self._logins:
            await self.stop()
            await self.start()

    def _save(self, values: dict[str, Any]) -> None:
        if self._save_settings is not None:
            self._save_settings(values)
        else:
            self.configure({**self._settings, **values})

    # ---- what actions use ----

    async def send_chat(self, message: str) -> None:
        """Writes in the chat of the account's channel (a bot account: the main account's) as that account."""
        await self._api().send_chat(self._channel_token().user_id, self._need_token().user_id, message)

    async def viewers(self) -> list[str]:
        """The login names of everyone in his chat right now, also those who never write (for the points'
        lurkers). Needs the "chatters" permission: PermissionError says to press Connect once."""
        token = self._need_token()
        channel = self._channel_token()
        if "moderator:read:chatters" not in token.scopes:
            raise PermissionError("Twitch: seeing who is in chat needs one more permission. Press Connect once "
                                  "under Connections → Twitch")
        found: list[str] = []
        cursor = ""
        for _ in range(20):  # 20 000 viewers
            answer = await self._api().helix("GET", "chat/chatters", params={
                "broadcaster_id": channel.user_id, "moderator_id": token.user_id, "first": 1000,
                **({"after": cursor} if cursor else {})})
            found += [str(one.get("user_login") or "") for one in answer.get("data") or []]
            cursor = str((answer.get("pagination") or {}).get("cursor") or "")
            if not cursor:
                break
        return [login for login in found if login]

    async def is_live(self) -> bool:
        """Whether his stream is on right now, as Twitch says."""
        answer = await self._api().helix("GET", "streams", params={"user_id": self._need_token().user_id})
        return bool(answer.get("data"))

    async def reward_titles(self) -> list[str]:
        return [r["title"] for r in await self._api().rewards(self._need_token().user_id)]

    async def reward_choices(self) -> dict[str, str]:
        """id → title of every channel point reward (a trigger or box keeps the id: a rename doesn't break it)."""
        return {r["id"]: r["title"] for r in await self._api().rewards(self._need_token().user_id)}

    async def create_reward(self, title: str, cost: int = 100, prompt: str = "", needs_text: bool = False) -> str:
        reward = await self._api().create_reward(self._need_token().user_id, title, int(cost), prompt,
                                                 bool(needs_text))
        return reward["id"]

    async def set_reward_paused(self, reward: str, paused: bool = True) -> None:
        """reward = its title. Only rewards made by the toolbox can be changed (Twitch's rule)."""
        user_id = self._need_token().user_id
        await self._api().update_reward(user_id, await self._reward_id(reward), is_paused=to_bool(paused))

    async def rewards(self) -> list[dict[str, Any]]:
        """Every channel point reward: title, id, cost, enabled, paused, by_toolbox (only those can be changed)."""
        user_id = self._need_token().user_id
        mine = {r["id"] for r in await self._api().rewards(user_id, only_mine=True)}
        return [{"title": r["title"], "id": r["id"], "cost": r.get("cost", 0), "enabled": r.get("is_enabled", True),
                 "paused": r.get("is_paused", False), "by_toolbox": r["id"] in mine}
                for r in await self._api().rewards(user_id)]

    # ---- the Twitch tool (RewardManager) ----

    async def list_rewards(self) -> list[TwitchReward]:
        user_id = self._need_token().user_id
        mine = {r["id"] for r in await self._api().rewards(user_id, only_mine=True)}
        return [TwitchReward.from_api(r, r["id"] in mine) for r in await self._api().rewards(user_id)]

    async def save_reward(self, reward: TwitchReward) -> TwitchReward:
        user_id = self._need_token().user_id
        if reward.id:
            return TwitchReward.from_api(await self._api().update_reward(user_id, reward.id, **reward.to_api()), True)
        return TwitchReward.from_api(await self._api().add_reward(user_id, reward.to_api()), True)

    async def delete_reward(self, reward_id: str) -> None:
        await self._api().delete_reward(self._need_token().user_id, reward_id)

    async def set_reward_enabled(self, reward: str, enabled: bool = True) -> None:
        """Switches a reward on or off (off = viewers don't see it, e.g. during a collab). Only rewards made by the
        toolbox (Twitch's rule)."""
        user_id = self._need_token().user_id
        await self._api().update_reward(user_id, await self._reward_id(reward), is_enabled=to_bool(enabled))

    async def create_marker(self, description: str = "") -> str:
        marker = await self._api().create_marker(self._need_token().user_id, str(description))
        return marker.get("id", "")

    async def finish_redeem(self, reward_id: str, redemption_id: str, refund: bool = False) -> None:
        """Marks a redeem done, or gives the points back (refund). Only for rewards made by the toolbox."""
        await self._api().set_redemption(self._need_token().user_id, reward_id, redemption_id,
                                         "CANCELED" if to_bool(refund) else "FULFILLED")

    async def _reward_id(self, reward: str) -> str:
        """The id of a reward given by its id (what the boxes keep now) or by its title (older flows)."""
        found = next((r for r in await self._api().rewards(self._need_token().user_id)
                      if r["id"] == str(reward) or r["title"].casefold() == str(reward).casefold()), None)
        if found is None:
            raise KeyError(f"no channel point reward {reward!r}")
        return found["id"]

    def default_flows(self) -> Path:
        return Path(__file__).parent / "twitch" / "default_flows.flows.toml"

    def add_actions(self, actions: ActionRegistry) -> None:
        TwitchChannelActions(self._helix, self._need_token).add_to(actions)
        TwitchStreamActions(self._helix, self._need_token, channel=self._channel_token).add_to(actions)
        TwitchViewerActions(self._helix, self._need_token).add_to(actions)
        downloader = None
        if self._folder is not None:
            program = GithubProgram(REPO, release_file(), program_name(),
                                    self._folder / "tools" / "twitch_downloader")
            downloader = TwitchClipDownloader(program, self._folder / "cache" / "clips")
        question = TwitchClipQuestion(self._folder / "cache" / "twitch_clip_question.json" if self._folder else None,
                                      self._transport)
        TwitchClipActions(TwitchClipFiles(self._transport, question=question), downloader).add_to(actions)
        for box in (SendChatMessage(self), CreateReward(self), PauseReward(self), RewardOnOff(self),
                    GetRewards(self), FinishRefundRedeem(self), StreamMarker(self)):
            actions.add_box(box, "twitch")

    # ---- internals ----

    async def _helix(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self._api().helix(method, path, **kwargs)

    async def helix(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Any Helix call with his login, for parts of the toolbox that aren't boxes (the widgets' channel
        lookups). Not connected raises, as the boxes do."""
        return await self._helix(method, path, **kwargs)

    async def _usable_token(self, name: str, token: OAuthToken | None) -> OAuthToken:
        """An account's saved login, renewed if needed; PermissionError when there is none that works for this
        app. A bot account needs only BOT_NEEDS."""
        if token is None:
            raise PermissionError("Not logged in yet: press Connect and allow the app in the browser")
        auth = self._auth()
        if token.expires_soon():
            token = await self._renew(auth, token)
        try:
            info = await auth.validate(token.access_token)
        except TwitchApiError as e:
            if e.status != 401:
                raise
            token = await self._renew(auth, token)
            info = await auth.validate(token.access_token)
        if info.get("client_id") != auth.client_id:
            raise PermissionError("The saved login belongs to another Twitch app: press Connect to log in again")
        missing = set(BOT_NEEDS if self.is_bot(name) else SCOPES) - set(info.get("scopes", []))
        if missing:
            raise PermissionError(f"The saved login lacks {', '.join(sorted(missing))}: log in again")
        token = OAuthToken(token.access_token, token.refresh_token, token.expires_at, tuple(info["scopes"]),
                            info["user_id"], info["login"])
        self._tokens.save_account(token, name)
        return token

    async def _renew(self, auth: TwitchAuth, token: OAuthToken) -> OAuthToken:
        try:
            answer = await auth.refresh(token.refresh_token)
        except TwitchApiError as e:
            raise PermissionError(f"The Twitch login expired ({e}): press Connect to log in again") from e
        renewed = OAuthToken.from_answer(answer, token.user_id, token.login)
        self._tokens.save_account(renewed)
        return renewed

    async def _login(self) -> OAuthToken:
        """Connect's login: the main account, every permission, Twitch's page opens on this PC."""
        def show(page: str, code: str) -> None:
            self._set_status(ConnectionStatus(ConnectionState.CONNECTING,
                                              f"Confirm the code {code} on the Twitch page that opened on the PC. "
                                              f"No tab? {page}"))
            self._open_browser(page)

        token = await self._login_with_code(self._auth(), SCOPES + EXTRA_SCOPES, show, self._login_timeout)
        self._tokens.save(token)  # the account that logged in is the main one
        return token

    async def _login_with_code(self, auth: TwitchAuth, scopes: tuple[str, ...], show: Callable[[str, str], None],
                               wait: float) -> OAuthToken:
        """A public app's login: show(page, code) tells where to confirm the code; asked until it was confirmed
        (at most `wait` seconds, and no longer than Twitch keeps the code)."""
        asked = await auth.device(scopes)
        show(asked["verification_uri"], asked["user_code"])
        loop = asyncio.get_running_loop()
        give_up = loop.time() + min(float(asked.get("expires_in", 1800)), wait)
        while True:
            answer = await auth.device_token(asked["device_code"], scopes)
            if answer is not None:
                break
            if loop.time() >= give_up:
                raise TimeoutError
            await asyncio.sleep(max(float(asked.get("interval", 5)), self._code_wait))
        info = await auth.validate(answer["access_token"])
        return OAuthToken.from_answer(answer, info["user_id"], info["login"])

    async def _access_token(self, renew: bool = False) -> str:
        name = self._account()
        self._need_token()
        async with self._refresh_locks.setdefault(name, asyncio.Lock()):
            token = self._logins[name]
            if renew or token.expires_soon():
                self._logins[name] = token = await self._renew(self._auth(), token)
        return token.access_token

    def _account(self) -> str:
        """The account the running work is for: its Account field / its own events, else the main one."""
        return ACCOUNT.get() or self.main_account()

    def _channel_token(self) -> OAuthToken:
        """The channel the account's chat and moderator work happen in: its own, or for a bot account the main
        account's (his plan: "the bot can write in his chat ... and do shoutouts ... if it is a mod")."""
        name = self._account()
        if not self.is_bot(name):
            return self._need_token()
        main = self._logins.get(self.main_account())
        if main is None:
            raise NotConnectedError(f"Twitch: the main account isn't connected ({self.status.detail or 'off'})")
        return main

    def _need_token(self) -> OAuthToken:
        if not self._settings["enabled"]:
            raise NotConnectedError("Twitch is switched off under Connections → Twitch")
        name = self._account()
        token = self._logins.get(name)
        if token is not None:
            return token
        if not self._logins:
            raise NotConnectedError(f"Twitch: {self.status.detail or 'not connected'}")
        if name not in self.account_names():
            raise NotConnectedError(f"Twitch: there is no account {name!r} (any more): Connections → Twitch")
        raise NotConnectedError(f"Twitch account {name}: {self._problems.get(name) or 'not logged in'}")

    def _auth(self) -> TwitchAuth:
        return TwitchAuth(BUILT_IN_CLIENT_ID, self._transport)

    def _api(self) -> TwitchApi:
        return TwitchApi(BUILT_IN_CLIENT_ID, self._access_token, self._transport)

    def _start_eventsub(self) -> None:
        """One event listener per account that listens (the main one, and the others he switched on): each runs
        as its account, so its subscriptions use its login and what it hears says which account it was."""
        loop = asyncio.get_running_loop()
        for name in self.listening_accounts():
            client = EventSubClient(self._subscribe, self._event, self._eventsub_state, self._eventsub_url,
                                    self._ws_connect)
            context = contextvars.copy_context()
            context.run(ACCOUNT.set, name)
            self._eventsubs[name] = loop.create_task(client.run(), context=context)

    def _start_follower_checks(self) -> None:
        """The failsafe (his ask of 2026-11-05): every listening account's newest followers, every
        follower_check seconds; a follow the live event missed comes as the same twitch.follow event."""
        loop = asyncio.get_running_loop()
        for name in self.listening_accounts():
            check = FollowerCheck(self._newest_followers, self._checked_follow, self._seen_by(name),
                                  self._follower_seconds)
            context = contextvars.copy_context()
            context.run(ACCOUNT.set, name)
            self._follower_checks[name] = loop.create_task(check.run(), context=context)

    def _follower_seconds(self) -> float:
        try:
            return float(self._settings.get("follower_check") or 0)
        except (TypeError, ValueError):
            return 60.0

    def _seen_by(self, name: str) -> SeenFollowers:
        if name not in self._seen:
            path = self._folder / FOLLOWERS / f"{PLATFORM}_{name}.json" if self._folder is not None else None
            self._seen[name] = SeenFollowers(path)
        return self._seen[name]

    async def _newest_followers(self) -> list[dict[str, Any]]:
        answer = await self._api().helix("GET", "channels/followers",
                                         params={"broadcaster_id": self._need_token().user_id, "first": 100})
        return [{"user": f.get("user_name") or "", "user_login": f.get("user_login") or "",
                 "user_id": f.get("user_id") or "", "followed_at": f.get("followed_at") or ""}
                for f in answer.get("data") or [] if isinstance(f, dict)]

    def _checked_follow(self, follower: dict[str, Any]) -> None:
        log.info("Twitch: %s followed %s (found by the follower check)", follower["user"], self._account())
        self._publish("twitch.follow", follower)

    def listening_accounts(self) -> list[str]:
        """The accounts whose own channel's events come in now: the main one first, then the others he switched
        on that are logged in (a bot account has no channel of interest)."""
        return self._accounts.listening(self.main_account(), self._logins)

    async def _subscribe(self, session_id: str) -> None:
        user_id = self._need_token().user_id
        failed = []
        for kind, version, condition in subscriptions(user_id):
            try:
                await self._api().subscribe(kind, condition, session_id, version)
            except TwitchApiError as e:  # e.g. subs / cheers before affiliate: the rest still works
                failed.append(kind)
                log.info("Twitch: no %s events for %s (%s)", kind, self._account(), e)
        if self._account() == self.main_account():
            self._missing_events = failed

    async def _event(self, kind: str, event: dict[str, Any]) -> None:
        found = to_event(kind, event)
        if found is not None:
            name, data = found
            if name in STREAM_EVENTS:
                data = {**data, **await self._stream_topic()}
            if name == FOLLOW and not self._seen_by(self._account()).fresh(data.get("user_id", "")):
                return  # the follower check had it already
            if self._raw is not None:
                self._raw(name, event)
            self._publish(name, data)

    def _publish(self, name: str, data: dict[str, Any]) -> None:
        self._events.publish(name, {**data, "platform": PLATFORM, ACCOUNT_FIELD: self._account(),
                                    MAIN_ACCOUNT_FIELD: self.main_account()})

    async def _stream_topic(self) -> dict[str, str]:
        """The stream's title and category (the game), asked when it goes live or ends: Twitch's message has
        neither. Empty when Twitch doesn't answer; the event still goes out."""
        try:
            answer = await self._api().helix("GET", "channels",
                                             params={"broadcaster_id": self._need_token().user_id})
        except Exception as e:
            log.info("Twitch: no title and category for the stream event (%s)", e)
            answer = {}
        info = (answer.get("data") or [{}])[0]
        return {"title": str(info.get("title") or ""), "category": str(info.get("game_name") or "")}

    def _eventsub_state(self, text: str) -> None:
        if self._account() != self.main_account():  # another account's listener: its own line on the tab
            self._problems[self._account()] = "" if text == "listening" else f"events: {text}"
            return
        self._listening = text
        if self._logins:
            self._show_connected()

    def _show_connected(self) -> None:
        missing = (("Not available", ", ".join(self._missing_events)),) if self._missing_events else ()
        main = self._logins.get(self.main_account())
        others = [name for name in self._logins if name != self.main_account()]
        more = (("Other accounts", ", ".join(others)),) if others else ()
        self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("Account", main.login if main else ""), *more, ("Events", self._listening), *missing)))


def _saved_as(token: OAuthToken, name: str) -> str:
    """The account's name after its check: its Twitch login (a renamed account, an old file without a name)."""
    return token.login.casefold() or name


def _reason(e: Exception) -> str:
    if isinstance(e, TimeoutError):
        return "Nobody allowed the app in the browser in time. Press Connect to try again."
    if isinstance(e, (PermissionError, TwitchApiError, ConnectionError)):
        return str(e)
    if isinstance(e, httpx.HTTPError):
        return f"can't reach Twitch: {e}"
    return str(e) or type(e).__name__
