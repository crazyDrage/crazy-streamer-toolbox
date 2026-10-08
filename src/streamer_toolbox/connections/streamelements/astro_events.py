"""What StreamElements' activity feed (the Astro websocket, topic channel.activities) says, as toolbox events.
Shapes taken from real messages (2026-10-03): data.type = tip, follow, subscriber, communityGiftPurchase, cheer,
raid, redemption (their loyalty store), merch, charityCampaignDonation; data.data = username, displayName,
amount, message, tier, items; data.isMock for the dashboard's test buttons."""
from typing import Any

ACTIVITY = "streamelements.activity"  # every activity, for flows (trigger "StreamElements activity", by type)
TIP = "tip"  # the toolbox's own tip event: a tip from StreamElements is one too
TOPIC = "channel.activities"


def activity_events(message: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """The toolbox events for one message of the feed: none for anything but an activity; an activity as
    `streamelements.activity`; a tip also as `tip` (Tip trigger, Tip alert, widgets' tip-latest)."""
    if message.get("type") != "message" or message.get("topic") != TOPIC:
        return []
    activity = message.get("data") or {}
    kind, data = str(activity.get("type") or ""), activity.get("data") or {}
    if not kind:
        return []
    user = str(data.get("displayName") or data.get("username") or "")
    text = str(data.get("message") or "").strip()
    amount = data.get("amount", 0) if isinstance(data.get("amount", 0), (int, float)) else 0
    events = [(ACTIVITY, {"type": kind, "user": user, "user_login": str(data.get("username") or ""),
                          "amount": amount, "message": text, "test": bool(activity.get("isMock")),
                          "platform": str(activity.get("provider") or "")})]
    if kind == "tip":
        events.append((TIP, {"user": user, "amount": amount, "currency": str(data.get("currency") or "").upper(),
                             "message": text, "platform": "streamelements"}))
    return events
