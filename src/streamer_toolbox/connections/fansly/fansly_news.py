import json
from typing import Any

from streamer_toolbox.core.events.chat_command import chat_command

CHAT = "fansly.chat"
TIP = "fansly.tip"  # a chat message with a tip in it; also the toolbox's `tip`
SUB = "fansly.sub"
PLATFORM = "fansly"
ONE, MANY = 10000, 10001  # the socket's message kinds: one event, a list of them
CHAT_EVENT, SUB_EVENT = 10, 53  # the event types inside
TIP_ATTACHMENT = 7


class FanslyNews:
    """A message from Fansly's chat socket, as toolbox events: chat messages, tips (a chat message that
    carries a tip: `fansly.tip` and the toolbox's `tip`, besides `fansly.chat`) and new subs.

    Fansly has no public API: this is the socket its website uses. The shapes are from the messages
    github.com/ZerGo0/fansly.streamerbot recorded (docs/protocol.md). A message is JSON whose `d` holds JSON as
    text, and that holds the event as text again, so each layer is read on its own. Guesses: a tip's amount is
    taken as thousandths of a dollar, as that extension does; whether a renewed sub also comes as a sub alert
    is not known."""

    def news(self, message: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        kind = message.get("t")
        if kind == ONE:
            found = [_layer(message.get("d"))]
        elif kind == MANY:
            many = _layer(message.get("d"), list)
            found = [_layer(one) for one in many]
        else:
            return []
        events: list[tuple[str, dict[str, Any]]] = []
        for one in found:
            event = _layer(one.get("event"))
            if event.get("type") == CHAT_EVENT:
                events += _chat(_layer(event.get("chatRoomMessage")))
            elif event.get("type") == SUB_EVENT:
                events += _sub(_layer(event.get("subAlert")))
        return events


def _chat(message: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    if not message:
        return []
    about = _layer(message.get("metadata"))
    tier = _layer(about.get("senderSubscription"))
    role = "broadcaster" if about.get("senderIsCreator") else "sub" if tier else "viewer"
    text = str(message.get("content") or "")
    command, args = chat_command(text)
    who = _who(message, "senderId")
    events = [(CHAT, {**who, "message": text, "command": command, "args": args,
                      "message_id": str(message.get("id") or ""), "color": str(message.get("usernameColor") or ""),
                      "role": role, "tier_name": str(tier.get("tierName") or ""),
                      "following": bool(about.get("senderIsFollowing")), "platform": PLATFORM})]
    amount = _tip(message.get("attachments"))
    if amount is not None:
        tip = {"user": who["user"], "amount": amount, "currency": "USD", "message": text, "platform": PLATFORM}
        events = [(TIP, {**who, "amount": amount, "message": text, "role": role, "platform": PLATFORM}),
                  ("tip", tip)] + events
    return events


def _sub(alert: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    if not alert:
        return []
    return [(SUB, {**_who(alert, "subscriberId"), "tier_name": str(alert.get("subscriptionTierName") or ""),
                   "streak": _whole(alert.get("subscriptionStreak")),
                   "total_days": _whole(alert.get("subscriptionTotalDays")), "role": "sub", "platform": PLATFORM})]


def _who(part: dict[str, Any], id_key: str) -> dict[str, str]:
    login = str(part.get("username") or "")
    return {"user": str(part.get("displayname") or login), "user_login": login.casefold(),
            "user_id": str(part.get(id_key) or part.get("senderId") or "")}


def _tip(attachments: Any) -> float | int | None:
    """The tip's amount in dollars, or None when the message carries no tip."""
    for one in _layer(attachments, list):
        one = _layer(one)
        if one.get("contentType") == TIP_ATTACHMENT:
            try:
                dollars = float(_layer(one.get("metadata")).get("amount", 0)) / 1000
            except (TypeError, ValueError):
                return 0
            return int(dollars) if dollars == int(dollars) else round(dollars, 2)
    return None


def _layer(value: Any, kind: type = dict) -> Any:
    """`value` as a dict (or list): Fansly sends inner parts as JSON text. Anything else gives an empty one."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return kind()
    return value if isinstance(value, kind) else kind()


def _whole(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
