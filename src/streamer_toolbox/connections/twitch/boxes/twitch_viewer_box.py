from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.core.interfaces.box import Box


Helix = Callable[..., Awaitable[dict[str, Any]]]
SCOPES = ("moderation:read", "channel:read:vips")


class TwitchViewerBox(Box):
    """What the twitch viewer boxes share (not a box itself: it has no run).

    "Get viewer role": asks Twitch what a viewer is in the channel: broadcaster, mod, VIP, sub or plain
    viewer. Twitch has no single "role of this user" request, so it asks three small ones (is this user one
    of my moderators / my VIPs / my subscribers) at the same time; the highest one is the role.

    A trigger never asks Twitch (it only has what the event says, and the role of the viewer's last chat
    message): a flow that needs the exact role of someone who didn't write yet uses this box."""

    def __init__(self, helix: Helix, me: Callable[[], OAuthToken]) -> None:
        self._helix = helix
        self._me = me

    async def _id(self, user: Any) -> str:
        login = str(user if user is not None else "").strip().lstrip("@").lower()
        if not login:
            raise ValueError("Which viewer? Give the name or the user id")
        found = _first(await self._helix("GET", "users", params={"login": login}))
        if not found:
            raise LookupError(f"Twitch has no user {login!r}")
        return str(found["id"])


def _first(answer: dict[str, Any]) -> dict[str, Any]:
    return (answer.get("data") or [{}])[0] if isinstance(answer, dict) else {}


def _tier(tier: Any) -> int:
    """Twitch's "1000" / "2000" / "3000" as 1, 2, 3."""
    try:
        return max(int(tier) // 1000, 1)
    except (TypeError, ValueError):
        return 1
