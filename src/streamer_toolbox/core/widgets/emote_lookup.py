import re
from typing import Any

import httpx

from streamer_toolbox.core.widgets.kept_answers import KeptAnswers

BTTV = "https://api.betterttv.net/3/cached"
BTTV_PICTURE = "https://cdn.betterttv.net/emote"
FFZ = "https://api.frankerfacez.com/v1"
GLOBAL = "global"


class EmoteLookup:
    """A channel's BetterTTV and FrankerFaceZ emotes, for widgets, in the shape StreamElements'
    `channels/<id>/emotes` had: {"bttvChannelEmotes", "bttvGlobalEmotes", "ffzChannelEmotes", "ffzGlobalEmotes"},
    each {emote's name: {"name", "_id", "type", "width", "height", "gif", "urls": {"1", "2", "4"}}}.
    StreamElements has removed that endpoint (it answers 410 Gone), so the toolbox asks BetterTTV and
    FrankerFaceZ themselves, by the channel's Twitch id. Kept like the channels (in the KeptAnswers given with
    the question: the asking widget's own); a service that can't be reached gives empty lists for its part
    and isn't kept. A channel that isn't known there has none.

    Left out: emotes whose name can't stand as a regular expression (`:'(`). Chat widgets build
    `new RegExp("\\b" + name + "\\b")` from each name, and one bad name stops every message."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def emotes(self, twitch_id: str, kept: KeptAnswers) -> dict[str, dict[str, Any]]:
        twitch_id = str(twitch_id).strip()
        everywhere = await self._part(kept, GLOBAL, f"{BTTV}/emotes/global", f"{FFZ}/set/global")
        here = await self._part(kept, twitch_id, f"{BTTV}/users/twitch/{twitch_id}", f"{FFZ}/room/id/{twitch_id}") \
            if twitch_id.isdigit() else {"bttv": {}, "ffz": {}}
        return {"bttvChannelEmotes": here["bttv"], "bttvGlobalEmotes": everywhere["bttv"],
                "ffzChannelEmotes": here["ffz"], "ffzGlobalEmotes": everywhere["ffz"]}

    async def _part(self, kept: KeptAnswers, key: str, bttv_url: str, ffz_url: str) -> dict[str, dict[str, Any]]:
        known, answer = kept.get(key)
        if known:
            return answer
        bttv, ffz = await self._ask(bttv_url), await self._ask(ffz_url)
        answer = {"bttv": _bttv(bttv or {}), "ffz": _ffz(ffz or {})}
        if bttv is not None and ffz is not None:  # both answered (also with "not known here")
            kept.keep(key, answer)
        return answer

    async def _ask(self, url: str) -> Any | None:
        """The answer; {} when the service doesn't know the channel; None when it can't be reached."""
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=10) as client:
                answer = await client.get(url, headers={"Accept": "application/json"})
            if answer.status_code == 404:
                return {}
            return answer.json() if answer.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None


def _bttv(answer: Any) -> dict[str, Any]:
    """BetterTTV: a list (the global ones) or {"channelEmotes", "sharedEmotes"}."""
    listed = answer if isinstance(answer, list) else \
        [*answer.get("channelEmotes", []), *answer.get("sharedEmotes", [])]
    return {e["code"]: {"name": e["code"], "_id": e["id"], "type": "bttv", "width": e.get("width", 28),
                        "height": e.get("height", 28), "gif": bool(e.get("animated")),
                        "urls": {"1": f"{BTTV_PICTURE}/{e['id']}/1x", "2": f"{BTTV_PICTURE}/{e['id']}/2x",
                                 "4": f"{BTTV_PICTURE}/{e['id']}/3x"}}
            for e in listed if _usable(e.get("code")) and e.get("id")}


def _ffz(answer: Any) -> dict[str, Any]:
    """FrankerFaceZ: {"sets": {id: {"emoticons": [...]}}}; of the global answer only its "default_sets"."""
    sets = answer.get("sets", {})
    wanted = [str(s) for s in answer["default_sets"]] if "default_sets" in answer else list(sets)
    found = {}
    for key in wanted:
        for e in sets.get(key, {}).get("emoticons", []):
            urls = {size: str(url) for size, url in (e.get("urls") or {}).items() if url}
            if not _usable(e.get("name")) or "1" not in urls:
                continue
            urls = {"1": urls["1"], "2": urls.get("2", urls["1"]), "4": urls.get("4", urls.get("2", urls["1"]))}
            found[e["name"]] = {"name": e["name"], "_id": str(e.get("id", "")), "type": "ffz",
                                "width": e.get("width", 28), "height": e.get("height", 28),
                                "gif": bool(e.get("animated")), "urls": urls}
    return found


def _usable(name: Any) -> bool:
    if not isinstance(name, str) or not name:
        return False
    try:
        re.compile(name)
    except re.error:
        return False
    return True
