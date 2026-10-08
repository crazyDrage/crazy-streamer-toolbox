import random
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from streamer_toolbox.connections.oauth.oauth_token import OAuthToken
from streamer_toolbox.core.actions.action_registry import ActionRegistry

Helix = Callable[..., Awaitable[dict[str, Any]]]  # (method, path, **httpx kwargs) → Twitch's answer
ANNOUNCEMENT_COLORS = ("primary", "blue", "green", "orange", "purple")
AD_LENGTHS = (30, 60, 90, 120, 150, 180)
ON_OFF = ("on", "off")
PREDICTION_ENDS = ("winner", "cancel", "lock")


class TwitchStreamActions:
    """Twitch boxes that need the permissions asked for on top of the login's basic ones (EXTRA_SCOPES in
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

    def add_to(self, actions: ActionRegistry) -> None:
        stream = {"group": "Stream"}
        actions.add("twitch.create_clip", self.create_clip, "Clips the last 30 seconds of your stream (only while "
                    "live); gives the clip's address", "Create clip", outputs={"id": "text", "url": "text",
                                                                               "edit_url": "text"}, **stream)
        actions.add("twitch.get_clips", self.clips, "The clips of a channel (yours when the name is empty), most "
                    "watched first, and one of them picked at random. E.g. for a shoutout that plays a clip",
                    "Get clips", hints={"user": "empty = your channel", "count": "how many to look at, up to 100",
                                        "max_seconds": "0 = any length", "days": "0 = all time"},
                    outputs={"count": "number", "clips": "list", "url": "text", "title": "text",
                             "seconds": "number", "thumbnail": "text", "id": "text"}, **stream)
        actions.add("twitch.run_ad", self.run_ad, "Starts an ad break now (only while live); gives its length "
                    "and how long until the next one is possible", "Run ad break",
                    options={"seconds": _ad_lengths}, outputs={"seconds": "number", "retry_after": "number"},
                    **stream)
        actions.add("twitch.start_raid", self.start_raid, "Starts a raid to that channel (Twitch runs its 90 "
                    "second countdown)", "Start raid", **stream)
        actions.add("twitch.cancel_raid", self.cancel_raid, "Cancels the raid that is counting down",
                    "Cancel raid", **stream)
        chat = {"group": "Chat"}
        actions.add("twitch.shoutout", self.shoutout, "Twitch's own shoutout (/shoutout) for that channel: only "
                    "while live, at most one every 2 minutes", "Shoutout", **chat)
        actions.add("twitch.announce", self.announce, "A highlighted announcement in your chat", "Announcement",
                    options={"color": _colors}, **chat)
        actions.add("twitch.chat_mode", self.chat_mode, "Switches chat modes: emote only, slow mode, followers "
                    "only, subscribers only. A field left empty stays as it is", "Chat mode",
                    options={"emote_only": _on_off, "subscribers_only": _on_off},
                    hints={"slow_seconds": "3 to 120, 0 = off, empty = leave",
                           "followers_minutes": "how long they must follow: 0 = any follower, -1 = off, "
                                                "empty = leave"}, **chat)
        actions.add("twitch.get_chatters", self.chatters, "Who is in your chat right now: the names and how many",
                    "Get chatters", live=True, outputs={"count": "number", "names": "list"}, **chat)
        viewers = {"group": "Viewers"}
        actions.add("twitch.timeout", self.timeout, "Times a viewer out; seconds 0 = a ban until you unban",
                    "Timeout / ban", hints={"seconds": "1 to 1209600 (two weeks); 0 = ban"}, **viewers)
        actions.add("twitch.unban", self.unban, "Ends a viewer's timeout or ban", "Untimeout / unban", **viewers)
        votes = {"group": "Polls and predictions"}
        actions.add("twitch.start_poll", self.start_poll, "Starts a poll; gives its id", "Start poll",
                    hints={"choices": "2 to 5, separated by commas (or a list)", "seconds": "15 to 1800"}, **votes)
        actions.add("twitch.end_poll", self.end_poll, "Ends the running poll and gives the result: the winner "
                    "and every choice with its votes", "End poll",
                    outputs={"winner": "text", "votes": "number", "choices": "list"}, **votes)
        actions.add("twitch.start_prediction", self.start_prediction, "Starts a prediction; gives its id",
                    "Start prediction", hints={"outcomes": "2 to 10, separated by commas (or a list)",
                                               "seconds": "30 to 1800"}, **votes)
        actions.add("twitch.end_prediction", self.end_prediction, "Ends the running prediction: winner = that "
                    "outcome won (points are paid out), cancel = everyone gets the points back, lock = no more "
                    "bets", "End prediction", options={"how": _prediction_ends},
                    hints={"winner": "the outcome's title, for how = winner"}, **votes)

    # ---- stream ----

    async def create_clip(self) -> dict[str, Any]:
        self._allowed("clips:edit")
        clip = _first(await self._helix("POST", "clips", params={"broadcaster_id": self._me().user_id}))
        if not clip:
            raise RuntimeError("Twitch made no clip (clips only work while you're live)")
        return {"id": clip["id"], "url": f"https://clips.twitch.tv/{clip['id']}", "edit_url": clip.get("edit_url", "")}

    async def clips(self, user: str = "", count: int = 50, max_seconds: float = 0, days: int = 0) -> dict[str, Any]:
        owner = (await self._user(user))["id"] if str(user).strip() else self._me().user_id
        params: dict[str, Any] = {"broadcaster_id": owner, "first": max(1, min(int(count), 100))}
        if int(days) > 0:
            now = self._now()
            params["started_at"] = (now - timedelta(days=int(days))).strftime("%Y-%m-%dT%H:%M:%SZ")
            params["ended_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        found = (await self._helix("GET", "clips", params=params)).get("data") or []
        clips = [{"id": c["id"], "url": c.get("url", ""), "title": c.get("title", ""),
                  "seconds": c.get("duration", 0), "views": c.get("view_count", 0),
                  "thumbnail": c.get("thumbnail_url", ""), "created": c.get("created_at", "")}
                 for c in found if not float(max_seconds) or c.get("duration", 0) <= float(max_seconds)]
        one = self._pick(clips) if clips else {}
        return {"count": len(clips), "clips": clips, "url": one.get("url", ""), "title": one.get("title", ""),
                "seconds": one.get("seconds", 0), "thumbnail": one.get("thumbnail", ""), "id": one.get("id", "")}

    async def run_ad(self, seconds: int = 60) -> dict[str, Any]:
        self._allowed("channel:edit:commercial")
        if int(seconds) not in AD_LENGTHS:
            raise ValueError(f"an ad break is {', '.join(map(str, AD_LENGTHS))} seconds long, not {seconds}")
        ad = _first(await self._helix("POST", "channels/commercial",
                                      json={"broadcaster_id": self._me().user_id, "length": int(seconds)}))
        return {"seconds": ad.get("length", int(seconds)), "retry_after": ad.get("retry_after", 0)}

    async def start_raid(self, user: str) -> None:
        self._allowed("channel:manage:raids")
        await self._helix("POST", "raids", params={"from_broadcaster_id": self._me().user_id,
                                                   "to_broadcaster_id": (await self._user(user))["id"]})

    async def cancel_raid(self) -> None:
        self._allowed("channel:manage:raids")
        await self._helix("DELETE", "raids", params={"broadcaster_id": self._me().user_id})

    # ---- chat ----

    async def shoutout(self, user: str) -> None:
        self._allowed("moderator:manage:shoutouts")
        me = self._me().user_id
        await self._helix("POST", "chat/shoutouts", params={
            "from_broadcaster_id": me, "to_broadcaster_id": (await self._user(user))["id"], "moderator_id": me})

    async def announce(self, message: str, color: str = "primary") -> None:
        self._allowed("moderator:manage:announcements")
        message = str(message).strip()
        if not message:
            raise ValueError("the announcement is empty")
        if color not in ANNOUNCEMENT_COLORS:
            raise ValueError(f"the colour is one of {', '.join(ANNOUNCEMENT_COLORS)}")
        await self._helix("POST", "chat/announcements", params=self._as_moderator(),
                          json={"message": message[:500], "color": color})

    async def chat_mode(self, emote_only: str = "", slow_seconds: Any = "", followers_minutes: Any = "",
                        subscribers_only: str = "") -> None:
        self._allowed("moderator:manage:chat_settings")
        settings: dict[str, Any] = {}
        if emote_only in ON_OFF:
            settings["emote_mode"] = emote_only == "on"
        if subscribers_only in ON_OFF:
            settings["subscriber_mode"] = subscribers_only == "on"
        if _given(slow_seconds):
            wait = int(slow_seconds)
            settings["slow_mode"] = wait > 0
            if wait > 0:
                settings["slow_mode_wait_time"] = max(3, min(wait, 120))
        if _given(followers_minutes):
            minutes = int(followers_minutes)
            settings["follower_mode"] = minutes >= 0
            if minutes >= 0:
                settings["follower_mode_duration"] = min(minutes, 129600)
        if not settings:
            raise ValueError("nothing to change: every field is empty")
        await self._helix("PATCH", "chat/settings", params=self._as_moderator(), json=settings)

    async def chatters(self) -> dict[str, Any]:
        self._allowed("moderator:read:chatters")
        answer = await self._helix("GET", "chat/chatters", params={**self._as_moderator(), "first": 1000})
        names = [str(c.get("user_name") or c.get("user_login") or "") for c in answer.get("data") or []]
        return {"count": answer.get("total", len(names)), "names": names}

    # ---- viewers ----

    async def timeout(self, user: str, seconds: int = 600, reason: str = "") -> None:
        self._allowed("moderator:manage:banned_users")
        ban: dict[str, Any] = {"user_id": (await self._user(user))["id"], "reason": str(reason)[:500]}
        if int(seconds) > 0:
            ban["duration"] = min(int(seconds), 1209600)
        await self._helix("POST", "moderation/bans", params=self._as_moderator(), json={"data": ban})

    async def unban(self, user: str) -> None:
        self._allowed("moderator:manage:banned_users")
        await self._helix("DELETE", "moderation/bans",
                          params={**self._as_moderator(), "user_id": (await self._user(user))["id"]})

    # ---- polls and predictions ----

    async def start_poll(self, title: str, choices: Any, seconds: int = 60) -> str:
        self._allowed("channel:manage:polls")
        titles = _titles(choices, 2, 5, "choices")
        poll = _first(await self._helix("POST", "polls", json={
            "broadcaster_id": self._me().user_id, "title": _title(title, 60),
            "choices": [{"title": t[:25]} for t in titles], "duration": max(15, min(int(seconds), 1800))}))
        return poll.get("id", "")

    async def end_poll(self) -> dict[str, Any]:
        self._allowed("channel:manage:polls")
        me = self._me().user_id
        poll = _first(await self._helix("GET", "polls", params={"broadcaster_id": me, "first": 1}))
        if poll.get("status") != "ACTIVE":
            raise RuntimeError("no poll is running")
        ended = _first(await self._helix("PATCH", "polls", json={"broadcaster_id": me, "id": poll["id"],
                                                                "status": "TERMINATED"})) or poll
        choices = [{"title": c.get("title", ""), "votes": c.get("votes", 0)} for c in ended.get("choices") or []]
        best = max(choices, key=lambda c: c["votes"], default={"title": "", "votes": 0})
        return {"winner": best["title"], "votes": best["votes"], "choices": choices}

    async def start_prediction(self, title: str, outcomes: Any, seconds: int = 120) -> str:
        self._allowed("channel:manage:predictions")
        titles = _titles(outcomes, 2, 10, "outcomes")
        prediction = _first(await self._helix("POST", "predictions", json={
            "broadcaster_id": self._me().user_id, "title": _title(title, 45),
            "outcomes": [{"title": t[:25]} for t in titles],
            "prediction_window": max(30, min(int(seconds), 1800))}))
        return prediction.get("id", "")

    async def end_prediction(self, how: str = "winner", winner: str = "") -> None:
        self._allowed("channel:manage:predictions")
        if how not in PREDICTION_ENDS:
            raise ValueError(f"how is one of {', '.join(PREDICTION_ENDS)}")
        me = self._me().user_id
        prediction = _first(await self._helix("GET", "predictions", params={"broadcaster_id": me, "first": 1}))
        if prediction.get("status") not in ("ACTIVE", "LOCKED"):
            raise RuntimeError("no prediction is running")
        change: dict[str, Any] = {"broadcaster_id": me, "id": prediction["id"],
                                  "status": {"winner": "RESOLVED", "cancel": "CANCELED", "lock": "LOCKED"}[how]}
        if how == "winner":
            wanted = str(winner).strip().casefold()
            found = next((o for o in prediction.get("outcomes") or []
                          if str(o.get("title", "")).casefold() == wanted), None)
            if found is None:
                titles = ", ".join(str(o.get("title", "")) for o in prediction.get("outcomes") or [])
                raise KeyError(f"the prediction has no outcome {winner!r} (it has: {titles})")
            change["winning_outcome_id"] = found["id"]
        await self._helix("PATCH", "predictions", json=change)

    # ---- internals ----

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
            raise KeyError(f"Twitch has no user {login!r}")
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
