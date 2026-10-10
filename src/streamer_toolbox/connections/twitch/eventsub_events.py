"""The EventSub subscriptions the toolbox makes and how each Twitch event becomes a toolbox event (its data is
what a flow's Start box gives). Keep EVENT_FIELDS (core/events/event_fields.py) in step with to_event()."""
from typing import Any

from streamer_toolbox.core.events.event_fields import CHAT_ROLES as ROLES

REDEMPTION = "channel.channel_points_custom_reward_redemption.add"
CHAT_MESSAGE = "channel.chat.message"
CHAT_DELETED = "channel.chat.message_delete"  # a moderator removed one message
CHAT_USER_CLEARED = "channel.chat.clear_user_messages"  # a ban or timeout: all of one chatter's messages go
CHAT_CLEARED = "channel.chat.clear"  # the whole chat was cleared
_BADGE_ROLES = {"broadcaster": "broadcaster", "moderator": "mod", "lead_moderator": "mod", "vip": "vip",
                "subscriber": "sub", "founder": "sub"}


def subscriptions(user_id: str) -> list[tuple[str, str, dict[str, str]]]:
    """(type, version, condition) of every subscription. Some fail for some channels (e.g. subs and cheers
    before affiliate); those are skipped, the others still work."""
    me = {"broadcaster_user_id": user_id}
    reader = {**me, "user_id": user_id}
    return [(REDEMPTION, "1", me), (CHAT_MESSAGE, "1", reader), (CHAT_DELETED, "1", reader),
            (CHAT_USER_CLEARED, "1", reader), (CHAT_CLEARED, "1", reader),
            ("channel.follow", "2", {**me, "moderator_user_id": user_id}),
            ("channel.subscribe", "1", me), ("channel.subscription.gift", "1", me),
            ("channel.subscription.message", "1", me), ("channel.cheer", "1", me),
            ("channel.raid", "1", {"to_broadcaster_user_id": user_id}),
            ("stream.online", "1", me), ("stream.offline", "1", me), ("channel.ad_break.begin", "1", me)]


def to_event(kind: str, e: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """A Twitch notification as (toolbox event, data); None for one the toolbox leaves out."""
    user = {"user": e.get("user_name") or "", "user_login": e.get("user_login") or "",
            "user_id": e.get("user_id") or ""}
    nobody = {"user": "", "user_login": "", "user_id": ""}  # an anonymous gift or cheer
    if kind == REDEMPTION:
        reward = e.get("reward", {})
        return "twitch.redeem", {
            "reward": reward.get("title", ""), "reward_id": reward.get("id", ""), "cost": reward.get("cost", 0),
            **user, "input": e.get("user_input", ""), "redemption_id": e.get("id", "")}
    if kind == CHAT_MESSAGE:
        source = e.get("source_broadcaster_user_id")
        if source and source != e.get("broadcaster_user_id"):  # shared chat in a collab: like SAMMI's "only own
            return None                                         # chat", the other channel's messages don't count
        written = (e.get("message") or {}).get("text", "")
        text = written.strip()
        command, _, args = text.partition(" ")
        return "twitch.chat", {
            "message": text, "command": command.casefold() if command.startswith("!") else "", "args": args.strip(),
            "user": e.get("chatter_user_name", ""), "user_login": e.get("chatter_user_login", ""),
            "message_id": e.get("message_id", ""), "role": role(e.get("badges") or []),
            "user_id": e.get("chatter_user_id", ""), "color": e.get("color", ""),
            "emotes": emotes(e.get("message") or {}, len(written) - len(written.lstrip()))}
    if kind == CHAT_DELETED:
        return "twitch.chat_deleted", {"user": e.get("target_user_name", ""),
                                       "user_login": e.get("target_user_login", ""),
                                       "user_id": e.get("target_user_id", ""), "message_id": e.get("message_id", "")}
    if kind == CHAT_USER_CLEARED:
        return "twitch.chat_deleted", {"user": e.get("target_user_name", ""),
                                       "user_login": e.get("target_user_login", ""),
                                       "user_id": e.get("target_user_id", ""), "message_id": ""}
    if kind == CHAT_CLEARED:
        return "twitch.chat_deleted", {"user": "", "user_login": "", "user_id": "", "message_id": ""}
    if kind == "channel.follow":
        return "twitch.follow", {**user, "followed_at": e.get("followed_at") or ""}
    if kind == "channel.subscribe":
        return "twitch.sub", {**user, "tier": _tier(e), "gift": bool(e.get("is_gift"))}
    if kind == "channel.subscription.message":
        return "twitch.resub", {**user, "tier": _tier(e), "months": e.get("cumulative_months", 0),
                                "message": (e.get("message") or {}).get("text", "")}
    if kind == "channel.subscription.gift":
        anonymous = bool(e.get("is_anonymous"))
        return "twitch.gift", {**(nobody if anonymous else user),
                               "amount": e.get("total", 0), "tier": _tier(e), "anonymous": anonymous}
    if kind == "channel.cheer":
        anonymous = bool(e.get("is_anonymous"))
        return "twitch.cheer", {**(nobody if anonymous else user),
                                "bits": e.get("bits", 0), "message": e.get("message", ""), "anonymous": anonymous}
    if kind == "channel.raid":
        return "twitch.raid", {"user": e.get("from_broadcaster_user_name", ""),
                               "user_login": e.get("from_broadcaster_user_login", ""),
                               "user_id": e.get("from_broadcaster_user_id", ""), "viewers": e.get("viewers", 0)}
    if kind == "stream.online":
        return "twitch.online", {"type": e.get("type", "live")}
    if kind == "stream.offline":
        return "twitch.offline", {}
    if kind == "channel.ad_break.begin":
        return "twitch.ad_break", {"seconds": e.get("duration_seconds", 0), "automatic": bool(e.get("is_automatic"))}
    return None


def emotes(message: dict[str, Any], cut: int = 0) -> list[dict[str, Any]]:
    """The Twitch emotes in a chat message: [{"name", "id", "start", "end"}], start and end = where the emote's
    name sits in the text (end is its last letter). Twitch sends the message in fragments (text, emote,
    mention, ...) that make up the text in order. cut: how many letters the toolbox trimmed off the front."""
    found, at = [], 0
    for fragment in message.get("fragments") or []:
        if not isinstance(fragment, dict):
            continue
        name = str(fragment.get("text") or "")
        emote = fragment.get("emote") if isinstance(fragment.get("emote"), dict) else None
        if fragment.get("type") == "emote" and emote and emote.get("id") and at >= cut:
            found.append({"name": name, "id": str(emote["id"]), "start": at - cut, "end": at - cut + len(name) - 1})
        at += len(name)
    return found


def role(badges: list[dict[str, Any]]) -> str:
    """The highest of broadcaster / mod / vip / sub a chatter's badges show, else viewer."""
    found = [_BADGE_ROLES[b.get("set_id", "")] for b in badges if b.get("set_id") in _BADGE_ROLES]
    return max(found, key=ROLES.index, default="viewer")


def _tier(e: dict[str, Any]) -> int:
    """Twitch sends "1000" / "2000" / "3000"; flows get 1 / 2 / 3."""
    try:
        return int(str(e.get("tier", "1000"))) // 1000
    except ValueError:
        return 1
