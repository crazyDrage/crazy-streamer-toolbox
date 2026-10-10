from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.core.events.event_fields import CHAT_ROLES

Helix = Callable[..., Awaitable[dict[str, Any]]]  # (method, path, **httpx kwargs) → Twitch's answer
# Twitch's list → the role it means, lowest first: someone in two lists gets the higher one
LISTS = (("subscriptions", "sub", "channel:read:subscriptions"), ("channels/vips", "vip", "channel:read:vips"),
         ("moderation/moderators", "mod", "moderation:read"))
PAGE = 100  # the most Twitch gives per request
MOST_PAGES = 50  # per list: 5000 names, then it stops (a request each)


class TwitchRoleList:
    """Everyone with a role in the channel, read from Twitch in whole lists: the subscribers, the VIPs and
    the moderators (100 per request, so 3 requests for a channel with up to 100 of each). For the RoleBook,
    when Settings → Viewer roles asks for it; the box "Get viewer role" asks about one viewer instead.

    `read` gives user id → role and the counts (requests, subs, vips, mods). A login without the rights for a
    list (from before 2026-10-10) raises PermissionError: press Connect once."""

    def __init__(self, helix: Helix, me: Callable[[], OAuthToken | None]) -> None:
        self._helix = helix
        self._me = me

    async def read(self) -> tuple[dict[str, str], dict[str, int]]:
        me = self._me()
        if me is None:
            raise ConnectionError("Twitch is not connected")
        missing = [scope for _, _, scope in LISTS if scope not in me.scopes]
        if missing:
            raise PermissionError("Twitch hasn't allowed this for the toolbox yet: press Connect once under "
                                  "Connections → Twitch and allow it in the browser (it needs "
                                  f"{', '.join(missing)})")
        roles: dict[str, str] = {}
        counts = {"requests": 0}
        for path, role, _ in LISTS:
            users, requests = await self._all(path, me.user_id)
            counts["requests"] += requests
            counts[role] = len(users)
            roles.update(dict.fromkeys(users, role))
        roles[me.user_id] = CHAT_ROLES[-1]
        return roles, counts

    async def _all(self, path: str, broadcaster: str) -> tuple[list[str], int]:
        """Every user id of one list, and how many requests it took."""
        users: list[str] = []
        after = ""
        for page in range(1, MOST_PAGES + 1):
            params = {"broadcaster_id": broadcaster, "first": PAGE, **({"after": after} if after else {})}
            answer = await self._helix("GET", path, params=params)
            users += [str(u["user_id"]) for u in answer.get("data") or [] if isinstance(u, dict) and u.get("user_id")]
            after = str((answer.get("pagination") or {}).get("cursor") or "")
            if not after:
                break
        return users, page
