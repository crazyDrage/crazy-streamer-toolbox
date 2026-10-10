from typing import Any

from streamer_toolbox.core.events.event_bus import EventBus

# a platform's event → the event that means the same on every platform
SAME = {
    "twitch.chat": "chat", "youtube.chat": "chat", "rumble.chat": "chat",
    "twitch.follow": "follow", "rumble.follow": "follow",
    "twitch.sub": "sub", "rumble.sub": "sub", "youtube.member": "sub",
    "twitch.resub": "resub", "youtube.member_milestone": "resub",
    "twitch.gift": "gift", "rumble.gift": "gift", "youtube.gift_members": "gift",
    "twitch.cheer": "cheer",
    "twitch.raid": "raid",
    "twitch.redeem": "redeem", "streamsocket.event": "redeem",
    "twitch.online": "online", "youtube.online": "online", "rumble.online": "online",
    "twitch.offline": "offline", "youtube.offline": "offline", "rumble.offline": "offline",
}
# what each of them always has (a platform that doesn't know a value gives the empty one)
FIELDS: dict[str, dict[str, Any]] = {
    "chat": {"user": "", "user_login": "", "message": "", "command": "", "args": "", "role": "viewer",
             "user_id": "", "message_id": "", "color": "", "emotes": []},
    "follow": {"user": "", "user_login": "", "user_id": "", "followed_at": "", "role": "viewer"},
    "sub": {"user": "", "user_login": "", "user_id": "", "tier": 1, "gift": False, "role": "viewer"},
    "resub": {"user": "", "user_login": "", "user_id": "", "tier": 1, "months": 0, "message": "", "role": "viewer"},
    "gift": {"user": "", "user_login": "", "user_id": "", "amount": 1, "tier": 1, "anonymous": False, "role": "viewer"},
    "cheer": {"user": "", "user_login": "", "user_id": "", "bits": 0, "message": "", "anonymous": False,
              "role": "viewer"},
    "raid": {"user": "", "user_login": "", "user_id": "", "viewers": 0, "role": "viewer"},
    "redeem": {"user": "", "user_login": "", "user_id": "", "reward": "", "input": "", "cost": 0, "reward_id": "",
               "redemption_id": "", "role": "viewer"},
    "online": {"title": "", "category": ""},
    "offline": {"title": "", "category": ""},
}


class CommonEvents:
    """One event for every platform. A Twitch follow and a Rumble follow each stay their own event
    (`twitch.follow`, `rumble.follow`), and both also become `follow`, with the same fields and `platform`
    saying where it came from. So a flow or an alert for "a follow" works for every platform he connects, now
    and later; one that should only run for Twitch keeps using the Twitch event, or checks `platform`.

    chat, follow, sub, resub, gift, cheer, raid, redeem, online, offline. A redeem is a Twitch channel point
    redeem or an event redeemed in the StreamSocket Events extension (reward = its name, cost = its bits).
    A YouTube membership counts as a sub, a member milestone as a resub. `source` names the platform's event."""

    def __init__(self, events: EventBus) -> None:
        self._events = events

    async def handle(self, kind: str, data: dict[str, Any]) -> None:
        same = SAME.get(kind)
        if same is not None:
            self._events.publish(same, common(kind, data))


def common(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    """A platform's event data in the common event's fields."""
    same = SAME[kind]
    given = dict(data)
    if kind == "streamsocket.event":
        given = {**given, "reward": data.get("event", ""), "reward_id": data.get("event_id", ""),
                 "cost": data.get("bits", 0)}
    if kind == "youtube.member_milestone":
        given["months"] = data.get("months", 0)
    found = {key: given.get(key, empty) for key, empty in FIELDS[same].items()}
    if "user_login" in found and not found["user_login"]:
        found["user_login"] = str(found.get("user") or "").casefold()  # platforms without a separate login
    return {**found, "platform": str(data.get("platform") or kind.partition(".")[0]), "source": kind}
