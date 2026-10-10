"""What Streamlabs' socket says (an "event" with a type and a list of messages), as toolbox events. Shapes taken
from real messages (2026-10-03, the Alert Box's test buttons): type = donation, bits, subscription, follow, raid,
twitchcharitydonation, loyalty_store_redemption, merch, and from YouTube superchat, superSticker, membershipGift,
jewelGift; each message has name / from, amount, currency, message (YouTube: comment), product, isTest /
isPreview. `for` says the platform (twitch_account, youtube_account, streamlabs). Their own housekeeping
(alertPlaying, streamlabels, ...-playing) is left out."""
from typing import Any

ACTIVITY = "streamlabs.activity"  # every activity, for flows (trigger "Streamlabs activity", by type)
TIP = "tip"  # the toolbox's own tip event: money for the streamer, whatever the platform calls it
# type → the platform a tip of that type came from; YouTube's two come in millionths of the currency
TIPS = {"donation": "streamlabs", "superchat": "youtube", "superSticker": "youtube"}
MICROS = ("superchat", "superSticker")
SKIP = ("alertPlaying", "streamlabels", "streamlabels.underlying")


def streamlabs_events(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """The toolbox events for one "event" of the socket: each message in it as `streamlabs.activity`; a donation,
    Super Chat or Super Sticker also as `tip` (Tip trigger, Tip alert, widgets' tip-latest)."""
    kind = str(payload.get("type") or "")
    messages = payload.get("message")
    if not kind or kind in SKIP or kind.endswith("-playing") or not isinstance(messages, list):
        return []
    events: list[tuple[str, dict[str, Any]]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        # a test donation is "from" Kevin with the streamer as "name"; a real one names the donor in both
        user = str(message.get("from") or message.get("name") or "")
        amount = _number(message.get("amount", message.get("viewers", message.get("jewelsAmount",
                                                                                   message.get("months", 0)))))
        if kind in MICROS:
            amount = _number(amount / 1_000_000)
        text = str(message.get("message") or message.get("comment") or "").strip()
        currency = str(message.get("currency") or "").upper()
        events.append((ACTIVITY, {
            "type": kind, "user": user, "amount": amount, "currency": currency, "message": text,
            "product": str(message.get("product") or ""),
            "test": bool(message.get("isTest") or message.get("isPreview")),
            "platform": str(payload.get("for") or "").removesuffix("_account")}))
        if kind in TIPS:
            events.append((TIP, {"user": user, "amount": amount, "currency": currency, "message": text,
                                 "platform": TIPS[kind]}))
    return events


def _number(value: Any) -> float | int:
    """Streamlabs sends amounts as numbers or as text ("13.37"); a whole one stays whole."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    return int(number) if number == int(number) else round(number, 2)
