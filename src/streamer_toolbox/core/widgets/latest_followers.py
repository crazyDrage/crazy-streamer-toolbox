import time
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.widgets.widget_session import RECENT, WidgetSession

Helix = Callable[..., Awaitable[dict[str, Any]]]
AGAIN_AFTER = 60.0  # seconds: follows that come in while the toolbox runs reach the session as events anyway


class LatestFollowers:
    """Who followed last, asked from Twitch with the toolbox's own login (Get Channel Followers), so a widget's
    "latest follower" is right from the first page on: also right after a start, and for follows that came
    while the toolbox was off. fill() puts the newest ones and the follower count into the session data; it
    asks Twitch at most once a minute and changes nothing when Twitch can't be asked (not logged in, down).

    Twitch has no such list for subs, cheers or tips: those are known from the events the toolbox saw."""

    def __init__(self, helix: Helix, own: Callable[[], dict[str, str]],
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._helix = helix
        self._own = own  # gives "providerId": the streamer's Twitch id
        self._clock = clock
        self._asked: float | None = None

    async def fill(self, session: WidgetSession) -> bool:
        """True if the session data has Twitch's answer now."""
        twitch_id = str(self._own().get("providerId") or "")
        if not twitch_id or (self._asked is not None and self._clock() - self._asked < AGAIN_AFTER):
            return False
        try:
            answer = await self._helix("GET", "channels/followers",
                                       params={"broadcaster_id": twitch_id, "first": RECENT})
        except Exception:  # not logged in, Twitch down or refusing: the next page asks again
            return False
        self._asked = self._clock()
        followers = [{"type": "follower", "name": str(f.get("user_name") or f.get("user_login") or ""),
                      "createdAt": str(f.get("followed_at") or "")} for f in answer.get("data") or []]
        session.know("follower", [f for f in followers if f["name"]], answer.get("total"))
        return True
