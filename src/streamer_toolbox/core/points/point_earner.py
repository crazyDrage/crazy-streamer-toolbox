import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.config.config_table_writer import ConfigTableWriter
from streamer_toolbox.core.interfaces.point_bank import PointBank
from streamer_toolbox.core.points.point_rules import PointRules
from streamer_toolbox.core.points.point_store import PointStore

log = logging.getLogger(__name__)
TABLE = "points"
CHAT = ("twitch.chat", "youtube.chat", "rumble.chat")
FOLLOW = ("twitch.follow", "rumble.follow")
SUB = ("twitch.sub", "twitch.resub", "rumble.sub", "youtube.member")
RAID = ("twitch.raid",)
CHEER = ("twitch.cheer",)
ONLINE = ("twitch.online", "youtube.online", "rumble.online")
OFFLINE = ("twitch.offline", "youtube.offline", "rumble.offline")
Say = Callable[[str, str], Awaitable[None]]  # (platform, text): writes in that platform's chat
Viewers = Callable[[], Awaitable[list[str]]]  # who is in the Twitch chat right now, by login
Live = Callable[[], Awaitable[bool]]  # whether the Twitch stream is on


class PointEarner:
    """Gives out points by the rules (PointRules): listens to the events (EventBus → handle) for chatters, the
    bonuses and the points command, and pays the chatters every few minutes (run, a task). Every platform's
    chat counts; a viewer's points are per platform.

    Time points go to those who wrote since the last payout, and (rule `lurkers`) to everyone Twitch lists
    as being in chat: `viewers` gives them, which needs a Twitch permission; while that isn't there
    `lurkers_note` says what to do and only those who wrote are paid. Other platforms have no such list.
    "Only while live": for the writers it follows the online / offline events (a toolbox started in the middle
    of a stream hasn't seen "online", so a platform that never said "offline" counts as live); for the lurkers
    Twitch is asked (`live`), because people sit in an offline chat for days."""

    def __init__(self, store: PointStore, rules: PointRules, writer: ConfigTableWriter | None = None,
                 say: Say | None = None, clock: Callable[[], float] = time.monotonic,
                 viewers: Viewers | None = None, live: Live | None = None,
                 bank: Callable[[], PointBank] | None = None, own: Callable[[], str] = lambda: "") -> None:
        self._own = own  # the streamer's Twitch login
        self._bank = bank  # where the points live now, for the command's answer (None: the store)
        self._viewers = viewers
        self._live = live
        self.lurkers_note = ""  # why the lurkers weren't paid last time ("" = they were, or it's switched off)
        self._store = store
        self.rules = rules
        self._writer = writer
        self._say = say
        self._clock = clock
        self._wrote: dict[str, set[str]] = {}  # platform → who wrote since the last payout
        self._off: set[str] = set()  # platforms that said "offline" (and not "online" since)

    def set_rules(self, rules: PointRules) -> None:
        self.rules = rules
        if self._writer is not None:
            self._writer.save(TABLE, rules.to_dict())

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        rules = self.rules
        if not rules.enabled:
            return
        platform = str(data.get("platform") or kind.partition(".")[0])
        user = str(data.get("user_login") or data.get("user") or "").strip()
        if kind in ONLINE:
            self._off.discard(platform)
        elif kind in OFFLINE:
            self._off.add(platform)
        elif kind in CHAT and user:
            if not (rules.only_live and platform in self._off) and self._earns(user):
                self._wrote.setdefault(platform, set()).add(user)
            if rules.command and str(data.get("command") or "") == rules.command.casefold():
                await self._answer(platform, str(data.get("user") or user), user)
        elif user and rules.source == "toolbox" and self._earns(user):  # in Mix It Up, it gives the bonuses
            bonus = (rules.on_follow if kind in FOLLOW else rules.on_sub if kind in SUB else
                     rules.on_raid if kind in RAID else
                     rules.per_100_bits * _whole(data.get("bits")) // 100 if kind in CHEER else 0)
            if bonus:
                self._store.add(user, bonus, platform)

    async def pay(self) -> int:
        """One payout: the time points to everyone who wrote since the last one, and to the lurkers. How many
        viewers got them."""
        wrote, self._wrote = self._wrote, {}
        if not self.rules.enabled or not self.rules.per_time or self.rules.source != "toolbox":
            return 0
        self.lurkers_note = ""
        if self.rules.lurkers and self._viewers is not None and "twitch" not in self._off:
            try:
                if not self.rules.only_live or self._live is None or await self._live():
                    wrote.setdefault("twitch", set()).update(
                        login for login in await self._viewers() if self._earns(login))
            except Exception as e:  # the permission is missing, Twitch isn't connected
                self.lurkers_note = str(e) or type(e).__name__
        paid = 0
        for platform, users in wrote.items():
            if self.rules.only_live and platform in self._off:
                continue
            self._store.add_many(sorted(users), self.rules.per_time, platform)
            paid += len(users)
        return paid

    def _earns(self, user: str) -> bool:
        """Not a name on the "never" list, and not the streamer unless he switched that on."""
        name = user.casefold()
        if name in self.rules.left_out():
            return False
        return self.rules.streamer_earns or name != str(self._own() or "").casefold()

    async def run(self) -> None:
        """Pays every `minutes` until cancelled (the rules may change while it runs)."""
        while True:
            await asyncio.sleep(self.rules.minutes * 60)
            try:
                await self.pay()
            except Exception:
                log.exception("points: a payout failed")

    async def _answer(self, platform: str, name: str, user: str) -> None:
        if self._say is None:
            return
        try:
            points = await self._bank().get(user, platform) if self._bank else self._store.get(user, platform)
        except Exception as e:  # Mix It Up is closed, or doesn't know the viewer
            log.info("points: %s's points could not be read (%s)", user, e)
            return
        text = self.rules.answer.replace("{user}", name).replace("{name}", self.rules.name) \
            .replace("{points}", str(points))
        try:
            await self._say(platform, text)
        except Exception as e:  # not connected, no permission to write: the stream goes on
            log.info("points: the answer was not written in %s chat (%s)", platform, e)


def _whole(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
