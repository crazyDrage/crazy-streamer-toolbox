from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.core.interfaces.box import Box

Helix = Callable[..., Awaitable[dict[str, Any]]]


class TwitchChannelBox(Box):
    """What the twitch channel boxes share (not a box itself: it has no run).

    Twitch boxes for the channel and its viewers that the login allows already (no new permissions): is the
    stream live (viewers, uptime), title and category (read and change), a viewer's profile, followers, the
    next ad break."""

    def __init__(self, helix: Helix, me: Callable[[], OAuthToken],
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self._helix = helix
        self._me = me
        self._now = now

    async def _user(self, user: Any) -> dict[str, Any]:
        login = str(user if user is not None else "").strip().lstrip("@").lower()
        if not login:
            raise ValueError("which user? (the name is empty)")
        found = _first(await self._helix("GET", "users", params={"login": login}))
        if not found:
            raise LookupError(f"Twitch has no user {login!r}")
        return found


def _first(answer: dict[str, Any]) -> dict[str, Any]:
    return (answer.get("data") or [{}])[0] if isinstance(answer, dict) else {}


def _time(value: Any) -> datetime | None:
    """Twitch times: RFC 3339 text ("2026-10-02T20:00:00Z"), for ads also a unix time; nothing → None."""
    if value in (None, "", 0):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
