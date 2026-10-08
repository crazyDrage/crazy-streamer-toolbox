from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.core.actions.action_registry import ActionRegistry

Helix = Callable[..., Awaitable[dict[str, Any]]]  # (method, path, **httpx kwargs) → Twitch's answer


class TwitchChannelActions:
    """Twitch boxes for the channel and its viewers that the login allows already (no new permissions): is the
    stream live (viewers, uptime), title and category (read and change), a viewer's profile, followers, the
    next ad break."""

    def __init__(self, helix: Helix, me: Callable[[], OAuthToken],
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self._helix = helix
        self._me = me
        self._now = now

    def add_to(self, actions: ActionRegistry) -> None:
        stream = {"group": "Stream"}
        actions.add("twitch.get_channel", self.channel, "Your channel now: live or not, viewers, how long you're "
                    "live, title, category, tags", "Channel info", live=True,
                    outputs={"live": "yes/no", "viewers": "number", "uptime_seconds": "number", "title": "text",
                             "category": "text", "tags": "list"}, **stream)
        actions.add("twitch.set_title", self.set_title, "Changes your stream title", "Set stream title",
                    hints={"title": "up to 140 characters"}, **stream)
        actions.add("twitch.set_category", self.set_category, "Changes your stream category (game) by its name, "
                    "e.g. Just Chatting; gives the name Twitch found", "Set category",
                    hints={"category": "the name as on Twitch; a close one is taken if it isn't exact"}, **stream)
        actions.add("twitch.get_ad_schedule", self.ad_schedule, "When the next ad break comes (seconds from now), "
                    "how long it is, snoozes left", "Next ad break", live=True,
                    outputs={"next_in_seconds": "number", "length_seconds": "number", "snoozes": "number"},
                    **stream)
        viewers = {"group": "Viewers"}
        actions.add("twitch.get_user", self.user, "A Twitch user by name: id, name, picture, about, since when, "
                    "partner / affiliate", "Get Twitch user",
                    outputs={"id": "text", "name": "text", "picture": "text", "about": "text", "created": "text",
                             "type": "text"}, **viewers)
        actions.add("twitch.get_followers", self.followers, "How many follow you; with a name also whether they "
                    "follow and since when", "Followers",
                    hints={"user": "empty = just the count"},
                    outputs={"count": "number", "follows": "yes/no", "since": "text"}, **viewers)

    async def channel(self) -> dict[str, Any]:
        me = self._me().user_id
        info = _first(await self._helix("GET", "channels", params={"broadcaster_id": me}))
        live = _first(await self._helix("GET", "streams", params={"user_id": me}))
        started = _time(live.get("started_at"))
        return {"live": bool(live), "viewers": live.get("viewer_count", 0),
                "uptime_seconds": round((self._now() - started).total_seconds()) if started else 0,
                "title": info.get("title", ""), "category": info.get("game_name", ""), "tags": info.get("tags", [])}

    async def set_title(self, title: str) -> None:
        title = str(title).strip()
        if not title:
            raise ValueError("the title is empty")
        if len(title) > 140:
            raise ValueError(f"Twitch titles are up to 140 characters, this one has {len(title)}")
        await self._helix("PATCH", "channels", params={"broadcaster_id": self._me().user_id}, json={"title": title})

    async def set_category(self, category: str) -> str:
        name = str(category).strip()
        if not name:
            raise ValueError("which category? (it is empty)")
        found = _first(await self._helix("GET", "games", params={"name": name})) or \
            _first(await self._helix("GET", "search/categories", params={"query": name, "first": 1}))
        if not found:
            raise KeyError(f"Twitch has no category like {name!r}")
        await self._helix("PATCH", "channels", params={"broadcaster_id": self._me().user_id},
                          json={"game_id": found["id"]})
        return found["name"]

    async def ad_schedule(self) -> dict[str, Any]:
        ads = _first(await self._helix("GET", "channels/ads", params={"broadcaster_id": self._me().user_id}))
        next_at = _time(ads.get("next_ad_at"))
        return {"next_in_seconds": max(round((next_at - self._now()).total_seconds()), 0) if next_at else 0,
                "length_seconds": ads.get("duration", 0), "snoozes": ads.get("snooze_count", 0)}

    async def user(self, user: str) -> dict[str, Any]:
        found = await self._user(user)
        return {"id": found["id"], "name": found.get("display_name") or found["login"],
                "picture": found.get("profile_image_url", ""), "about": found.get("description", ""),
                "created": found.get("created_at", ""), "type": found.get("broadcaster_type", "")}

    async def followers(self, user: str = "") -> dict[str, Any]:
        params = {"broadcaster_id": self._me().user_id}
        if str(user).strip():
            params["user_id"] = (await self._user(user))["id"]
        answer = await self._helix("GET", "channels/followers", params=params)
        follow = _first(answer)
        return {"count": answer.get("total", 0), "follows": bool(follow) if "user_id" in params else False,
                "since": follow.get("followed_at", "") if "user_id" in params else ""}

    async def _user(self, user: Any) -> dict[str, Any]:
        login = str(user if user is not None else "").strip().lstrip("@").lower()
        if not login:
            raise ValueError("which user? (the name is empty)")
        found = _first(await self._helix("GET", "users", params={"login": login}))
        if not found:
            raise KeyError(f"Twitch has no user {login!r}")
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
