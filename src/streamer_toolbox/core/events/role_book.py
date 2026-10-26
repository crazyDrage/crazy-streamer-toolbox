from collections.abc import Callable, Mapping
from typing import Any

from streamer_toolbox.core.events.event_fields import CHAT_ROLES, EVENT_FIELDS

SUBS = ("sub", "resub", "twitch.sub", "twitch.resub", "rumble.sub", "fansly.sub", "youtube.member",
        "youtube.member_milestone")
IDS = ("user_id", "user_login", "user")


class RoleBook:
    """Who is a sub, VIP or mod, for the events that don't say it. Only a chat message tells a viewer's role
    (its badges); a redeem, a follow, a sub or a raid does not. So the book remembers the role each chatter
    had in their last message, per platform, and `fill` (the event bus calls it for every event) gives every
    event that names a user a `role` from it: a role filter then works on those triggers too.

    Someone who didn't write in chat since the toolbox started counts as "viewer" (kept in memory only), except
    the streamer (`owner` gives their Twitch id) and whoever just subbed (at least "sub"). `load` takes a
    platform's whole list (RoleLoader: Twitch's mods, VIPs and subs, when Settings → Viewer roles says so):
    then also who didn't write yet has their role, and a later chat message still corrects it."""

    def __init__(self, owner: Callable[[], str] = lambda: "") -> None:
        self._owner = owner
        self._roles: dict[tuple[str, str], str] = {}

    def load(self, platform: str, roles: Mapping[str, str]) -> None:
        """A platform's whole list (user id or name → role), e.g. Twitch's mods, VIPs and subs: it replaces
        what was known for that platform, so who is not in it is a plain viewer again."""
        self._roles = {key: role for key, role in self._roles.items() if key[0] != platform}
        self._roles.update({(platform, str(who).casefold()): role for who, role in roles.items()
                            if who and role in CHAT_ROLES})

    def fill(self, kind: str, data: dict[str, Any]) -> dict[str, Any]:
        if "role" not in EVENT_FIELDS.get(kind, ()) or not isinstance(data, dict):
            return data
        platform = str(data.get("platform") or kind.partition(".")[0])
        keys = [(platform, str(data[key]).casefold()) for key in IDS if data.get(key)]
        if data.get("role") in CHAT_ROLES:
            if kind.rpartition(".")[2] == "chat":  # a chat message: the newest word on this viewer
                self._roles.update(dict.fromkeys(keys, data["role"]))
            return data  # or an event made from a filled one (the common one)
        role = next((self._roles[key] for key in keys if key in self._roles), "viewer")
        if kind in SUBS:
            role = max(role, "sub", key=CHAT_ROLES.index)
        owner = str(self._owner() or "")
        if owner and platform == "twitch" and str(data.get("user_id") or "") == owner:
            role = "broadcaster"
        return {**data, "role": role}
