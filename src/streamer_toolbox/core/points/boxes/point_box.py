from collections.abc import Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box
from streamer_toolbox.core.interfaces.point_bank import PointBank

PLATFORMS = {"twitch": "Twitch", "youtube": "YouTube", "rumble": "Rumble"}


class PointBox(Box):
    """What the point boxes share (not a box itself: it has no run).

    The Points boxes: the toolbox's own currency per viewer, for flows (a command that costs points, a reward
    that gives some, a leaderboard). The viewer is usually Start's user_login, the platform Start's platform.
    `bank` gives where the points live right now (the toolbox's store or Mix It Up's currency): he can switch
    on the Points page without touching a flow."""

    def __init__(self, bank: Callable[[], PointBank]) -> None:
        self._bank = bank


def _viewer(viewer: str) -> str:
    name = str(viewer).strip().lstrip("@")
    if not name:
        raise ValueError("a viewer's name is needed (wire Start's user_login)")
    return name


def _whole(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise ValueError(f"a whole number is needed, not {value!r}") from None
