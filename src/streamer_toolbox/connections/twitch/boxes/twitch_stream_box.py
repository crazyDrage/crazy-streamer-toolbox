import random
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.core.interfaces.box import Box


Helix = Callable[..., Awaitable[dict[str, Any]]]
ANNOUNCEMENT_COLORS = ("primary", "blue", "green", "orange", "purple")
AD_LENGTHS = (30, 60, 90, 120, 150, 180)
ON_OFF = ("on", "off")
PREDICTION_ENDS = ("winner", "cancel", "lock")


class TwitchStreamBox(Box):
    """What the twitch stream boxes share (not a box itself: it has no run).

    Twitch boxes that need the permissions asked for on top of the login's basic ones (EXTRA_SCOPES in
    twitch_auth; he said yes to all of them on 2026-10-03): clip, shoutout, announcement, poll, prediction,
    raid, ad break, chat modes, timeout / ban, who is in chat. A login from before doesn't have them yet: such
    a box then says "press Connect once", the rest of the toolbox keeps working. Also "Get clips" (a channel's
    clips, one picked at random; Twitch asks no permission for that)."""

    def __init__(self, helix: Helix, me: Callable[[], OAuthToken],
                 pick: Callable[[list], Any] = random.choice,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self._helix = helix
        self._me = me
        self._pick = pick
        self._now = now

    def _allowed(self, scope: str) -> None:
        if scope not in self._me().scopes:
            raise PermissionError("Twitch hasn't allowed this for the toolbox yet: press Connect once under "
                                  f"Connections → Twitch and allow it in the browser (it needs {scope})")

    def _as_moderator(self) -> dict[str, str]:
        me = self._me().user_id
        return {"broadcaster_id": me, "moderator_id": me}

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


def _given(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _title(title: Any, longest: int) -> str:
    title = str(title).strip()
    if not title:
        raise ValueError("the title is empty")
    return title[:longest]


def _titles(given: Any, fewest: int, most: int, what: str) -> list[str]:
    """Choices from a list or from text separated by commas."""
    parts = given if isinstance(given, (list, tuple)) else str(given if given is not None else "").split(",")
    titles = [str(part).strip() for part in parts if str(part).strip()]
    if not fewest <= len(titles) <= most:
        raise ValueError(f"{what}: {fewest} to {most} are needed, there are {len(titles)}")
    return titles


async def _colors() -> list[str]:
    return list(ANNOUNCEMENT_COLORS)


async def _ad_lengths() -> list[str]:
    return [str(length) for length in AD_LENGTHS]


async def _on_off() -> list[str]:
    return ["", *ON_OFF]


async def _prediction_ends() -> list[str]:
    return list(PREDICTION_ENDS)
