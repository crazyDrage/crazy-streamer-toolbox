"""A message of YouTube's live chat (a liveChatMessage resource: snippet.type + its details, authorDetails) as
toolbox events. Money and memberships come through the chat too: Super Chat, Super Sticker, new member, member
milestone, gifted memberships. Field names from developers.google.com/youtube/v3/live/docs/liveChatMessages.
YouTube has no event for a new subscriber (its free "follow")."""
from typing import Any

CHAT = "youtube.chat"
SUPERCHAT = "youtube.superchat"
SUPERSTICKER = "youtube.supersticker"
MEMBER = "youtube.member"
MILESTONE = "youtube.member_milestone"
GIFT = "youtube.gift_members"
ONLINE = "youtube.online"
OFFLINE = "youtube.offline"
TIP = "tip"
PLATFORM = "youtube"
ENDED = "chatEndedEvent"


def youtube_events(message: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """The toolbox events for one chat message; [] for the kinds flows have no use for (bans, deleted
    messages, polls, "you got a gifted membership")."""
    snippet = message.get("snippet") if isinstance(message.get("snippet"), dict) else {}
    author = message.get("authorDetails") if isinstance(message.get("authorDetails"), dict) else {}
    kind = str(snippet.get("type") or "")
    user = str(author.get("displayName") or "")
    here = {"platform": PLATFORM}
    if kind == "textMessageEvent":
        text = str(_details(snippet, "textMessageDetails").get("messageText") or snippet.get("displayMessage") or "")
        command, _, args = text.partition(" ")
        return [(CHAT, {"user": user, "message": text,
                        "command": command.casefold() if command.startswith("!") else "", "args": args.strip(),
                        "role": _role(author), "user_id": str(author.get("channelId") or ""),
                        "message_id": str(message.get("id") or ""), **here})]
    if kind in ("superChatEvent", "superStickerEvent"):
        sticker = kind == "superStickerEvent"
        details = _details(snippet, "superStickerDetails" if sticker else "superChatDetails")
        text = str((details.get("superStickerMetadata") or {}).get("altText") or "") if sticker \
            else str(details.get("userComment") or "")
        money = {"user": user, "amount": _money(details.get("amountMicros")),
                 "currency": str(details.get("currency") or "").upper(), "message": text, **here}
        return [(SUPERSTICKER if sticker else SUPERCHAT, money), (TIP, dict(money))]
    if kind == "newSponsorEvent":
        details = _details(snippet, "newSponsorDetails")
        return [(MEMBER, {"user": user, "level": str(details.get("memberLevelName") or ""),
                          "upgrade": bool(details.get("isUpgrade")), **here})]
    if kind == "memberMilestoneChatEvent":
        details = _details(snippet, "memberMilestoneChatDetails")
        return [(MILESTONE, {"user": user, "months": _whole(details.get("memberMonth")),
                             "level": str(details.get("memberLevelName") or ""),
                             "message": str(details.get("userComment") or ""), **here})]
    if kind == "membershipGiftingEvent":
        details = _details(snippet, "membershipGiftingDetails")
        return [(GIFT, {"user": user, "amount": _whole(details.get("giftMembershipsCount")),
                        "level": str(details.get("giftMembershipsLevelName") or ""), **here})]
    return []


def _details(snippet: dict[str, Any], key: str) -> dict[str, Any]:
    return snippet[key] if isinstance(snippet.get(key), dict) else {}


def _role(author: dict[str, Any]) -> str:
    """The toolbox's chat role (CHAT_ROLES): a member counts as sub."""
    if author.get("isChatOwner"):
        return "broadcaster"
    if author.get("isChatModerator"):
        return "mod"
    return "sub" if author.get("isChatSponsor") else "viewer"


def _money(micros: Any) -> float | int:
    """YouTube gives money in millionths of the currency."""
    try:
        amount = float(micros) / 1_000_000
    except (TypeError, ValueError):
        return 0
    return int(amount) if amount == int(amount) else round(amount, 2)


def _whole(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
