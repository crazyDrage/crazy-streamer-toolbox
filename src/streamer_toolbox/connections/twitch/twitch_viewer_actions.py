import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.core.actions.action_registry import ActionRegistry

Helix = Callable[..., Awaitable[dict[str, Any]]]  # (method, path, **httpx kwargs) → Twitch's answer
SCOPES = ("moderation:read", "channel:read:vips")  # in EXTRA_SCOPES: a login from before doesn't have them


class TwitchViewerActions:
    """"Get viewer role": asks Twitch what a viewer is in the channel: broadcaster, mod, VIP, sub or plain
    viewer. Twitch has no single "role of this user" request, so it asks three small ones (is this user one
    of my moderators / my VIPs / my subscribers) at the same time; the highest one is the role.

    A trigger never asks Twitch (it only has what the event says, and the role of the viewer's last chat
    message): a flow that needs the exact role of someone who didn't write yet uses this box."""

    def __init__(self, helix: Helix, me: Callable[[], OAuthToken]) -> None:
        self._helix = helix
        self._me = me

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("twitch.viewer_role", self.role, "What a viewer is in your channel, asked from Twitch now: "
                    "broadcaster, mod, vip, sub or viewer (the highest one), and each as yes / no. Works for "
                    "someone who never wrote in chat", "Get viewer role", group="Viewers", live=True,
                    outputs={"role": "text", "is_mod": "yes/no", "is_vip": "yes/no", "is_sub": "yes/no",
                             "tier": "number"},
                    hints={"user": "The viewer's name; not needed with a user id",
                           "user_id": "Wire the trigger's user_id into it: saves the look-up by name"})

    async def role(self, user: str = "", user_id: str = "") -> dict[str, Any]:
        missing = [scope for scope in SCOPES if scope not in self._me().scopes]
        if missing:
            raise PermissionError("Twitch hasn't allowed this for the toolbox yet: press Connect once under "
                                  "Connections → Twitch and allow it in the browser (it needs "
                                  f"{', '.join(missing)})")
        me = self._me().user_id
        viewer = str(user_id if user_id is not None else "").strip() or await self._id(user)
        if viewer == me:
            return {"role": "broadcaster", "is_mod": True, "is_vip": False, "is_sub": False, "tier": 0}
        ask = {"broadcaster_id": me, "user_id": viewer}
        mod, vip, sub = (_first(a) for a in await asyncio.gather(
            self._helix("GET", "moderation/moderators", params=ask),
            self._helix("GET", "channels/vips", params=ask), self._helix("GET", "subscriptions", params=ask)))
        role = "mod" if mod else "vip" if vip else "sub" if sub else "viewer"
        return {"role": role, "is_mod": bool(mod), "is_vip": bool(vip), "is_sub": bool(sub),
                "tier": _tier(sub.get("tier")) if sub else 0}

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
