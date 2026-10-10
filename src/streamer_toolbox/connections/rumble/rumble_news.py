from collections import deque
from typing import Any

CHAT = "rumble.chat"
FOLLOW = "rumble.follow"
SUB = "rumble.sub"
GIFT = "rumble.gift"
RANT = "rumble.rant"  # a paid chat message; also the toolbox's `tip`
ONLINE = "rumble.online"
OFFLINE = "rumble.offline"
TIP = "tip"
PLATFORM = "rumble"
# a chat badge of Rumble → the toolbox's chat role (CHAT_ROLES); the highest one counts
ROLES = {"admin": "broadcaster", "moderator": "mod", "recurring_subscription": "sub", "locals_supporter": "sub"}
ORDER = ("viewer", "sub", "vip", "mod", "broadcaster")


class RumbleNews:
    """What is new in an answer of Rumble's Live Stream API, as toolbox events. The API has no feed: each
    answer holds the latest followers, subscribers, gifted subs and, per live stream, the recent chat messages
    and rants (paid messages). So this remembers what it has seen. The first answer only fills the memory: what
    was there before the toolbox listened is not news.

    Field names are from Rumble's documented example answer (rumble.support, "How to use Rumble's Live Stream
    API"); the gifted subs' fields are read loosely because the example doesn't show a filled one."""

    def __init__(self, keep: int = 2000) -> None:
        self._seen: deque[tuple] = deque(maxlen=keep)
        self._live: dict[str, str] = {}  # stream id → title, of the streams that are live
        self._first = True

    def news(self, answer: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        events: list[tuple[str, dict[str, Any]]] = []
        for one in _list(answer.get("followers"), "recent_followers"):
            self._add(events, ("follow", _name(one), one.get("followed_on")), FOLLOW, {
                "user": _name(one), "followed_at": str(one.get("followed_on") or "")})
        for one in _list(answer.get("subscribers"), "recent_subscribers"):
            self._add(events, ("sub", _name(one), one.get("subscribed_on")), SUB, {
                "user": _name(one), "amount": _dollars(one)})
        for one in _list(answer.get("gifted_subs"), "recent_gifted_subs"):
            who = str(one.get("purchased_by") or _name(one))
            self._add(events, ("gift", who, one.get("total_gifts"), one.get("purchased_on") or one.get("created_on")),
                      GIFT, {"user": who, "amount": _whole(one.get("total_gifts", 1))})
        streams = [s for s in answer.get("livestreams") or [] if isinstance(s, dict)]
        for stream in streams:
            chat = stream.get("chat") if isinstance(stream.get("chat"), dict) else {}
            for one in _list(chat, "recent_messages"):
                text = str(one.get("text") or "")
                command, _, args = text.partition(" ")
                self._add(events, ("chat", _name(one), one.get("created_on"), text), CHAT, {
                    "user": _name(one), "message": text,
                    "command": command.casefold() if command.startswith("!") else "", "args": args.strip(),
                    "role": _role(one.get("badges"))})
            for one in _list(chat, "recent_rants"):
                text = str(one.get("text") or "")
                key = ("rant", _name(one), one.get("created_on"), text)
                if self._add(events, key, RANT, {"user": _name(one), "amount": _dollars(one), "message": text}):
                    events.append((TIP, {"user": _name(one), "amount": _dollars(one), "currency": "USD",
                                         "message": text, "platform": PLATFORM}))
        live = {str(s.get("id")): str(s.get("title") or "") for s in streams if s.get("is_live")}
        if not self._first:
            events += [(ONLINE, {"title": title, "platform": PLATFORM})
                       for stream, title in live.items() if stream not in self._live]
            events += [(OFFLINE, {"title": title, "platform": PLATFORM})
                       for stream, title in self._live.items() if stream not in live]
        self._live = live
        self._first = False
        return events

    def _add(self, events: list, key: tuple, kind: str, data: dict[str, Any]) -> bool:
        if key in self._seen:
            return False
        self._seen.append(key)
        if self._first:
            return False
        events.append((kind, {**data, "platform": PLATFORM}))
        return True


def _list(part: Any, key: str) -> list[dict[str, Any]]:
    """The entries under `key`, oldest first (Rumble lists the newest first)."""
    found = part.get(key) if isinstance(part, dict) else None
    return [one for one in reversed(found) if isinstance(one, dict)] if isinstance(found, list) else []


def _name(one: dict[str, Any]) -> str:
    return str(one.get("username") or one.get("user") or "")


def _role(badges: Any) -> str:
    roles = [ROLES.get(str(badge), "viewer") for badge in badges] if isinstance(badges, list) else []
    return max(roles, key=ORDER.index, default="viewer")


def _dollars(one: dict[str, Any]) -> float | int:
    try:
        amount = float(one.get("amount_dollars", float(one.get("amount_cents", 0)) / 100))
    except (TypeError, ValueError):
        return 0
    return int(amount) if amount == int(amount) else round(amount, 2)


def _whole(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1
