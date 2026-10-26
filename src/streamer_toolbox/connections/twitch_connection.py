import asyncio
import logging
import secrets
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
from streamer_toolbox.connections.oauth.oauth_code_listener import OAuthCodeListener
from streamer_toolbox.connections.twitch.eventsub_events import subscriptions, to_event
from streamer_toolbox.connections.twitch.twitch_api import TwitchApi
from streamer_toolbox.connections.twitch.twitch_api_error import TwitchApiError
from streamer_toolbox.connections.twitch.twitch_auth import BUILT_IN_CLIENT_ID, EXTRA_SCOPES, SCOPES, TwitchAuth
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
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.core.actions.action_registry import ActionRegistry
from streamer_toolbox.core.connections.connection_base import ConnectionBase
from streamer_toolbox.core.connections.connection_state import ConnectionState
from streamer_toolbox.core.connections.connection_status import ConnectionStatus
from streamer_toolbox.core.connections.not_connected_error import NotConnectedError
from streamer_toolbox.core.connections.setting_field import SettingField
from streamer_toolbox.core.data.box_value import to_bool
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.system.github_program import GithubProgram
from streamer_toolbox.core.flows.flow_trigger import REWARDS
from streamer_toolbox.core.interfaces.reward_manager import RewardManager

REDEEM = "twitch.redeem"
CHAT = "twitch.chat"
log = logging.getLogger(__name__)
PLATFORM = "twitch"  # every Twitch event says so (a flow on the common events tells them apart by it)
STREAM_EVENTS = ("twitch.online", "twitch.offline")  # these also say the stream's title and category


class TwitchConnection(ConnectionBase, RewardManager):
    """The streamer's Twitch account: redeems, chat, follows, subs, gifts, cheers, raids, stream online / offline
    and ad breaks start flows (twitch/eventsub_events.py has what each gives), plus chat, reward and marker
    actions.

    Login only happens on Connect; starting the toolbox never opens it. Without an app of his own (Client ID
    and Secret empty) it uses the toolbox's built-in app: Twitch's page opens with a short code to confirm, no
    setup. With an app of his own, a browser tab asks to allow it (like VTube Studio's popup). The login is kept
    in config/secrets/twitch_token.json and renewed by itself.
    """

    id = "twitch"
    title = "Twitch"
    icon = "live_tv"

    def __init__(self, settings: dict[str, Any], tokens: OAuthTokenStore, events: EventBus,
                 transport: httpx.AsyncBaseTransport | None = None, ws_connect: Callable[..., Any] = websockets.connect,
                 eventsub_url: str = EVENTSUB_URL, open_browser: Callable[[str], Any] = webbrowser.open,
                 login_timeout: float = 180, code_wait: float = 1.0, folder: Path | None = None,
                 raw: Callable[[str, dict[str, Any]], None] | None = None) -> None:
        super().__init__({"client_id": "", "client_secret": "", "redirect_url": "http://localhost:17563"},
                         settings)
        self._tokens = tokens
        self._folder = folder  # the settings folder: where the clip downloader and its clips are kept
        self._events = events
        self._raw = raw  # gets (event name, Twitch's own message) right before the event goes out
        self._transport = transport
        self._ws_connect = ws_connect
        self._eventsub_url = eventsub_url
        self._open_browser = open_browser
        self._login_timeout = login_timeout
        self._code_wait = code_wait  # the shortest pause between two asks "did he confirm the code?"
        self._token: OAuthToken | None = None
        self._eventsub: asyncio.Task | None = None
        self._announce: asyncio.Task | None = None  # keeps the reward list task alive
        self._listening = "not yet"
        self._missing_events: list[str] = []
        self._refresh_lock = asyncio.Lock()

    def fields(self) -> list[SettingField]:
        return [SettingField("client_id", "Client ID (only for an app of your own)",
                             hint="leave Client ID and Secret empty to log in with the toolbox's own Twitch app: "
                                  "press Connect and confirm the code on Twitch's page. Own app: "
                                  "dev.twitch.tv/console → your app"),
                SettingField("client_secret", "Client Secret (only for an app of your own)", secret=True),
                SettingField("redirect_url", "Redirect URL (only for an app of your own)",
                             hint="must be one of the app's OAuth Redirect URLs (default: http://localhost:17563)")]

    # ---- Connection ----

    async def start(self) -> None:
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING))
        try:
            self._token = await self._usable_token(self._settings, self._tokens.load())
        except Exception as e:
            self._set_status(ConnectionStatus(ConnectionState.ERROR, _reason(e)))
            return
        self._start_eventsub()
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
        if self._eventsub is not None:
            self._eventsub.cancel()
            try:
                await self._eventsub
            except (asyncio.CancelledError, Exception):
                pass
        self._eventsub = None
        self._listening = "not yet"
        self._set_status(ConnectionStatus(ConnectionState.OFF))

    async def test(self, settings: dict[str, Any]) -> ConnectionStatus:
        """Uses the saved login if it still works for this app, else logs in through the browser. A login that
        works but is from before a permission was added (EXTRA_SCOPES) logs in again too, so Connect brings the
        new permissions; if that isn't finished, the saved login stays as it is."""
        if settings.get("client_secret") and not settings.get("client_id"):
            return ConnectionStatus(ConnectionState.ERROR, "A Client Secret needs its Client ID (or leave both "
                                                           "empty to use the toolbox's own Twitch app)")
        try:
            try:
                token = await self._usable_token(settings, self._tokens.load())
            except PermissionError:
                token = await self._login(settings)
            else:
                if set(EXTRA_SCOPES) - set(token.scopes):
                    token = await self._login(settings)
        except Exception as e:
            return ConnectionStatus(ConnectionState.ERROR, _reason(e))
        return ConnectionStatus(ConnectionState.CONNECTED, "", (("Account", token.login),))

    # ---- what actions use ----

    async def send_chat(self, message: str) -> None:
        token = self._need_token()
        await self._api().send_chat(token.user_id, token.user_id, message)

    async def viewers(self) -> list[str]:
        """The login names of everyone in his chat right now, also those who never write (for the points'
        lurkers). Needs the "chatters" permission: PermissionError says to press Connect once."""
        token = self._need_token()
        if "moderator:read:chatters" not in token.scopes:
            raise PermissionError("Twitch: seeing who is in chat needs one more permission. Press Connect once "
                                  "under Connections → Twitch")
        found: list[str] = []
        cursor = ""
        for _ in range(20):  # 20 000 viewers
            answer = await self._api().helix("GET", "chat/chatters", params={
                "broadcaster_id": token.user_id, "moderator_id": token.user_id, "first": 1000,
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

    def add_actions(self, actions: ActionRegistry) -> None:
        TwitchChannelActions(self._helix, self._need_token).add_to(actions)
        TwitchStreamActions(self._helix, self._need_token).add_to(actions)
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

    async def _usable_token(self, settings: dict[str, Any], token: OAuthToken | None) -> OAuthToken:
        """The saved login, renewed if needed; PermissionError when there is none that works for this app."""
        if token is None:
            raise PermissionError("Not logged in yet: press Connect and allow the app in the browser")
        auth = self._auth(settings)
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
        missing = set(SCOPES) - set(info.get("scopes", []))
        if missing:
            raise PermissionError(f"The saved login lacks {', '.join(sorted(missing))}: press Connect again")
        token = OAuthToken(token.access_token, token.refresh_token, token.expires_at, tuple(info["scopes"]),
                            info["user_id"], info["login"])
        self._tokens.save(token)
        return token

    async def _renew(self, auth: TwitchAuth, token: OAuthToken) -> OAuthToken:
        try:
            answer = await auth.refresh(token.refresh_token)
        except TwitchApiError as e:
            raise PermissionError(f"The Twitch login expired ({e}): press Connect to log in again") from e
        renewed = OAuthToken.from_answer(answer, token.user_id, token.login)
        self._tokens.save(renewed)
        return renewed

    async def _login(self, settings: dict[str, Any]) -> OAuthToken:
        auth = self._auth(settings)
        if auth.public:
            return await self._login_with_code(auth)
        port = httpx.URL(auth.redirect_uri).port or 80
        listener = OAuthCodeListener("localhost", port)  # v4 and v6: browsers may try ::1 first
        state = secrets.token_urlsafe(16)
        try:
            await listener.start(state)
        except OSError as e:
            raise ConnectionError(f"port {port} is busy (another tool logging in?): {e}") from e
        url = auth.authorize_url(state)
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING,
                                          f"Allow the app in the browser tab that opened on the PC. No tab? {url}"))
        self._open_browser(url)
        code = await listener.wait(self._login_timeout)
        answer = await auth.exchange(code)
        info = await auth.validate(answer["access_token"])
        token = OAuthToken.from_answer(answer, info["user_id"], info["login"])
        self._tokens.save(token)
        return token

    async def _login_with_code(self, auth: TwitchAuth) -> OAuthToken:
        """A public app's login: Twitch's page opens with the code filled in; asked until he confirmed it."""
        asked = await auth.device()
        page, code = asked["verification_uri"], asked["user_code"]
        self._set_status(ConnectionStatus(ConnectionState.CONNECTING,
                                          f"Confirm the code {code} on the Twitch page that opened on the PC. "
                                          f"No tab? {page}"))
        self._open_browser(page)
        loop = asyncio.get_running_loop()
        give_up = loop.time() + min(float(asked.get("expires_in", 1800)), self._login_timeout)
        while True:
            answer = await auth.device_token(asked["device_code"])
            if answer is not None:
                break
            if loop.time() >= give_up:
                raise TimeoutError
            await asyncio.sleep(max(float(asked.get("interval", 5)), self._code_wait))
        info = await auth.validate(answer["access_token"])
        token = OAuthToken.from_answer(answer, info["user_id"], info["login"])
        self._tokens.save(token)
        return token

    async def _access_token(self, renew: bool = False) -> str:
        token = self._need_token()
        async with self._refresh_lock:
            token = self._token
            if renew or token.expires_soon():
                self._token = token = await self._renew(self._auth(self._settings), token)
        return token.access_token

    def _need_token(self) -> OAuthToken:
        if not self._settings["enabled"]:
            raise NotConnectedError("Twitch is switched off under Connections → Twitch")
        if self._token is None:
            raise NotConnectedError(f"Twitch: {self.status.detail or 'not connected'}")
        return self._token

    def _auth(self, settings: dict[str, Any]) -> TwitchAuth:
        """His own app when its Client ID is filled in, else the toolbox's built-in public one."""
        own = str(settings.get("client_id") or "").strip()
        return TwitchAuth(own or BUILT_IN_CLIENT_ID, str(settings.get("client_secret") or "") if own else "",
                          settings["redirect_url"], self._transport)

    def _api(self) -> TwitchApi:
        return TwitchApi(self._auth(self._settings).client_id, self._access_token, self._transport)

    def _start_eventsub(self) -> None:
        client = EventSubClient(self._subscribe, self._event, self._eventsub_state, self._eventsub_url,
                                self._ws_connect)
        self._eventsub = asyncio.get_running_loop().create_task(client.run())

    async def _subscribe(self, session_id: str) -> None:
        user_id = self._need_token().user_id
        failed = []
        for kind, version, condition in subscriptions(user_id):
            try:
                await self._api().subscribe(kind, condition, session_id, version)
            except TwitchApiError as e:  # e.g. subs / cheers before affiliate: the rest still works
                failed.append(kind)
                log.info("Twitch: no %s events (%s)", kind, e)
        self._missing_events = failed

    async def _event(self, kind: str, event: dict[str, Any]) -> None:
        found = to_event(kind, event)
        if found is not None:
            name, data = found
            if name in STREAM_EVENTS:
                data = {**data, **await self._stream_topic()}
            if self._raw is not None:
                self._raw(name, event)
            self._events.publish(name, {**data, "platform": PLATFORM})

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
        self._listening = text
        if self._token is not None:
            self._show_connected()

    def _show_connected(self) -> None:
        missing = (("Not available", ", ".join(self._missing_events)),) if self._missing_events else ()
        self._set_status(ConnectionStatus(ConnectionState.CONNECTED, "", (
            ("Account", self._token.login), ("Events", self._listening), *missing)))


def _reason(e: Exception) -> str:
    if isinstance(e, TimeoutError):
        return "Nobody allowed the app in the browser in time. Press Connect to try again."
    if isinstance(e, (PermissionError, TwitchApiError, ConnectionError)):
        return str(e)
    if isinstance(e, httpx.HTTPError):
        return f"can't reach Twitch: {e}"
    return str(e) or type(e).__name__
