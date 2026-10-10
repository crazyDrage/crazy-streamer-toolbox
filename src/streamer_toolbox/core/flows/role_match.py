"""Who may start a trigger, by role: the editor's checkboxes ↔ the trigger's match."""
from collections.abc import Iterable
from typing import Any

from streamer_toolbox.core.events.event_fields import CHAT_ROLES

ROLE_TITLES = {"viewer": "Plain viewers", "sub": "Subs", "vip": "VIPs", "mod": "Mods", "broadcaster": "You"}
# the match keys that are about the role: "roles" is what the editor saves ({"roles": "vip, mod"});
# "who" (that role and up) and "who_max" (that role and down) are older and still work
ROLE_KEYS = ("roles", "who", "who_max")
ROLES_HELP = ("Everyone counts as their highest role only: a mod who is also a sub is a mod. For \"everyone but "
              "mods\" tick Plain viewers, Subs and VIPs.")


def roles_of(match: dict[str, Any]) -> list[str]:
    """The roles a trigger's match lets through, lowest first; all of them when it says nothing."""
    if match.get("roles"):
        wanted = {role.strip().casefold() for role in str(match["roles"]).split(",")}
        return [role for role in CHAT_ROLES if role in wanted]
    low = CHAT_ROLES.index(match["who"]) if match.get("who") in CHAT_ROLES else 0
    high = CHAT_ROLES.index(match["who_max"]) if match.get("who_max") in CHAT_ROLES else len(CHAT_ROLES) - 1
    return list(CHAT_ROLES[low:high + 1])


def roles_match(roles: Iterable[str]) -> dict[str, str]:
    """The ticked roles as the trigger's match key; none when all are ticked (everyone), or none is."""
    ticked = [role for role in CHAT_ROLES if role in set(roles)]
    return {} if len(ticked) in (0, len(CHAT_ROLES)) else {"roles": ", ".join(ticked)}


def roles_text(roles: Iterable[str]) -> str:
    """"Everyone", or "VIPs, Mods"."""
    ticked = [role for role in CHAT_ROLES if role in set(roles)]
    return "Everyone" if len(ticked) in (0, len(CHAT_ROLES)) else ", ".join(ROLE_TITLES[role] for role in ticked)
