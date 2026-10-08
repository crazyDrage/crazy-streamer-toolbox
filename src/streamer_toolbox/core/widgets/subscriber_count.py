import time
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.widgets.widget_session import WidgetSession

Helix = Callable[..., Awaitable[dict[str, Any]]]
AGAIN_AFTER = 60.0  # seconds


class SubscriberCount:
    """How many subscribers the channel has and how many sub points, asked from Twitch with the toolbox's own
    login (Get Broadcaster Subscriptions: its `total` and `points`), so a widget's subscriber count or sub goal
    is right without StreamElements. fill() puts both into the session data (`subscriber-total`,
    `subscriber-points`); it asks Twitch at most once a minute and changes nothing when Twitch can't be asked.

    Who subscribed *last* is not something Twitch tells: its list has no dates and no order (checked against a
    real channel, 2026-10-04). That comes from the events the toolbox saw."""

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
            answer = await self._helix("GET", "subscriptions", params={"broadcaster_id": twitch_id, "first": 1})
        except Exception:  # not logged in, no permission (not an affiliate), Twitch down: the next page asks again
            return False
        self._asked = self._clock()
        session.know("subscriber", [], answer.get("total"))
        session.points(answer.get("points"))
        return True
