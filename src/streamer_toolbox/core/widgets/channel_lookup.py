import re
from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.widgets.kept_answers import KeptAnswers

Helix = Callable[..., Awaitable[dict[str, Any]]]
LOGIN = re.compile(r"[A-Za-z0-9_]{1,25}")


class ChannelLookup:
    """Who a channel is, for widgets, from the toolbox's own Twitch login instead of StreamElements' public API.
    Widgets ask StreamElements' `channels/<name or id>` for a channel's picture, platform and Twitch id; on a
    widget page that question comes here (streamelements_links rewrites the address, widget_router has the
    route) and this answers in StreamElements' shape from Twitch's Get Users. None = can't say (no such Twitch
    user, Twitch not connected, Twitch refused).

    Answers are kept in the KeptAnswers given with the question (the asking widget's own, in its data
    folder): six hours, a profile picture rarely changes; also "not there". A failure isn't kept.

    `who` is a Twitch login name, a Twitch id, or the streamer's own StreamElements account id (own() gives
    "username", "providerId" and "id", as WidgetPage has them)."""

    def __init__(self, helix: Helix, own: Callable[[], dict[str, str]] | None = None) -> None:
        self._helix = helix
        self._own = own or (lambda: {})

    async def channel(self, who: str, kept: KeptAnswers) -> dict[str, Any] | None:
        who = str(who).strip().lstrip("#").casefold()
        own = self._own()
        if who and who == str(own.get("id") or "").casefold():
            who = str(own.get("username") or "").casefold()  # his StreamElements id: himself
        if not LOGIN.fullmatch(who):
            return None
        known, answer = kept.get(who)
        if known:
            return answer
        try:
            user = await self._user(who)
        except Exception:  # not logged in, Twitch down or refusing: not kept, the next page asks again
            return None
        answer = _as_streamelements(user, own) if user else None
        kept.keep(who, answer)
        return answer

    async def _user(self, who: str) -> dict[str, Any] | None:
        """By id if it's a number (and by name if no one has that id: a name can be digits too)."""
        for key in (("id", "login") if who.isdigit() else ("login",)):
            found = (await self._helix("GET", "users", params={key: who})).get("data") or []
            if found:
                return found[0]
        return None


def _as_streamelements(user: dict[str, Any], own: dict[str, str]) -> dict[str, Any]:
    """A Twitch user the way StreamElements' channel answer has it. `_id` is StreamElements' account id there;
    only his own is known here, anyone else gets the Twitch id."""
    twitch_id, login = str(user.get("id", "")), str(user.get("login", ""))
    is_own = twitch_id == str(own.get("providerId") or "") and bool(own.get("id"))
    name = str(user.get("display_name") or login)
    kind = str(user.get("broadcaster_type") or "")
    return {"_id": own["id"] if is_own else twitch_id, "provider": "twitch", "providerId": twitch_id,
            "username": login, "alias": login, "displayName": name,
            "avatar": str(user.get("profile_image_url", "")), "broadcasterType": kind,
            "isPartner": kind == "partner", "inactive": False, "suspended": False,
            "profile": {"title": f"{name}'s profile"}}
