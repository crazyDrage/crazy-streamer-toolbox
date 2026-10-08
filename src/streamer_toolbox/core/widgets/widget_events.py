"""Toolbox events in StreamElements' words: what a custom widget's code gets in onEventReceived as
obj.detail.listener and obj.detail.event. Keep in step with EVENT_FIELDS (what the toolbox events hold)."""
import time
from html import escape
from typing import Any

SOMEONE = "Anonymous"  # StreamElements' name for a gifter / cheerer without one
# a chat role of the toolbox → Twitch's badge name
BADGES = {"sub": "subscriber", "vip": "vip", "mod": "moderator", "broadcaster": "broadcaster"}
TEST_CHAT = "Hello from the toolbox!"
COMMON = {"follow": "twitch.follow", "sub": "twitch.sub", "resub": "twitch.resub", "gift": "twitch.gift",
          "cheer": "twitch.cheer", "raid": "twitch.raid", "chat": "twitch.chat"}
EMOTE_URL = "https://static-cdn.jtvnw.net/emoticons/v2/{id}/default/dark/{size}"  # Twitch's own emote pictures

# Test buttons: listener → (its name in the tool, an example event)
TEST_EVENTS: dict[str, tuple[str, dict[str, Any]]] = {
    "follower-latest": ("Follow", {"type": "follower", "name": "TestViewer"}),
    "subscriber-latest": ("Sub", {"type": "subscriber", "name": "TestViewer", "amount": 3, "tier": "1000",
                                  "message": "three months!", "gifted": False}),
    "cheer-latest": ("Cheer", {"type": "cheer", "name": "TestViewer", "amount": 100, "message": "take my bits"}),
    "raid-latest": ("Raid", {"type": "raid", "name": "TestViewer", "amount": 42}),
    "tip-latest": ("Tip", {"type": "tip", "name": "TestViewer", "amount": 5, "message": "for snacks",
                           "userCurrency": "EUR"}),
    "message": ("Chat message", {}),  # filled by chat_message, so its time is now
}


def se_event(kind: str, data: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """(listener, event) for a toolbox event, None for one StreamElements has no word for."""
    if kind in COMMON:  # a common event from another platform, in the words of Twitch's (never both)
        if data.get("platform") == "twitch":
            return None
        kind = COMMON[kind]
    name = str(data.get("user") or SOMEONE)
    if kind == "twitch.follow":
        return "follower-latest", {"type": "follower", "name": name}
    if kind == "twitch.sub":
        return "subscriber-latest", {"type": "subscriber", "name": name, "amount": 1, "tier": _tier(data),
                                     "message": "", "gifted": bool(data.get("gift"))}
    if kind == "twitch.resub":
        return "subscriber-latest", {"type": "subscriber", "name": name, "amount": data.get("months", 1),
                                     "tier": _tier(data), "message": str(data.get("message") or ""), "gifted": False}
    if kind == "twitch.gift":  # the gifter's event: StreamElements calls the first one of a gift train bulkGifted
        return "subscriber-latest", {"type": "subscriber", "name": name, "sender": name,
                                     "amount": data.get("amount", 1), "tier": _tier(data), "message": "",
                                     "bulkGifted": True}
    if kind == "twitch.cheer":
        return "cheer-latest", {"type": "cheer", "name": name, "amount": data.get("bits", 0),
                                "message": str(data.get("message") or "")}
    if kind == "twitch.raid":
        return "raid-latest", {"type": "raid", "name": name, "amount": data.get("viewers", 0)}
    if kind == "tip":
        return "tip-latest", {"type": "tip", "name": name, "amount": data.get("amount", 0),
                              "message": str(data.get("message") or ""),
                              "userCurrency": str(data.get("currency") or "")}
    if kind == "twitch.chat":
        return "message", chat_message(name, str(data.get("user_login") or name).casefold(),
                                       str(data.get("message") or ""), str(data.get("message_id") or ""),
                                       str(data.get("role") or "viewer"), str(data.get("user_id") or ""),
                                       str(data.get("color") or ""), data.get("emotes") or [],
                                       str(data.get("platform") or "twitch"))
    if kind == "twitch.chat_deleted":  # one message; or every message of a chatter; or (no user) the whole chat
        if data.get("message_id"):
            return "delete-message", {"msgId": str(data["message_id"])}
        return "delete-messages", {"userId": str(data.get("user_id") or "")}
    return None


def chat_message(name: str, login: str, text: str, message_id: str = "", role: str = "viewer",
                 user_id: str = "", color: str = "", emotes: list[dict[str, Any]] | None = None,
                 service: str = "twitch") -> dict[str, Any]:
    """A chat message as StreamElements hands it to a widget: the fields chat widgets and helper libraries
    (se-tools) read, with Twitch's tags that say who it is (badges, mod, user-id), and its Twitch emotes
    (twitch.chat's `emotes`): in the tags the way Twitch's chat writes them ("id:start-end"), as a list with
    the pictures' addresses, and in renderedText as pictures."""
    badge = BADGES.get(role, "")
    emotes = [emote for emote in emotes or [] if isinstance(emote, dict) and emote.get("id")]
    places: dict[str, list[str]] = {}
    for emote in emotes:
        places.setdefault(str(emote["id"]), []).append(f"{emote['start']}-{emote['end']}")
    tags = {"badges": f"{badge}/1" if badge else "", "color": color, "display-name": name,
            "emotes": "/".join(f"{emote_id}:{','.join(spots)}" for emote_id, spots in places.items()),
            "id": message_id, "mod": "1" if role == "mod" else "0", "subscriber": "1" if role == "sub" else "0",
            "user-id": user_id, "room-id": "", "user-type": "mod" if role == "mod" else ""}
    badges = [{"type": badge, "version": "1", "url": "", "description": badge}] if badge else []
    listed = [{"type": "twitch", "name": str(emote.get("name") or ""), "id": str(emote["id"]), "gif": False,
               "urls": {"1": EMOTE_URL.format(id=emote["id"], size="1.0"),
                        "2": EMOTE_URL.format(id=emote["id"], size="2.0"),
                        "4": EMOTE_URL.format(id=emote["id"], size="3.0")},
               "start": emote["start"], "end": emote["end"]} for emote in emotes]
    return {"service": service, "renderedText": _rendered(text, listed),
            "data": {"time": int(time.time() * 1000), "tags": tags, "nick": login, "userId": user_id,
                     "displayName": name, "displayColor": color, "badges": badges, "channel": "", "text": text,
                     "isAction": False, "emotes": listed, "msgId": message_id}}


def _rendered(text: str, emotes: list[dict[str, Any]]) -> str:
    """The message as HTML: the viewer's words escaped, each emote as its picture."""
    html, at = "", 0
    for emote in sorted(emotes, key=lambda one: one["start"]):
        if emote["start"] < at or emote["end"] >= len(text):
            continue
        urls = emote["urls"]
        html += escape(text[at:emote["start"]]) + (
            f'<img src="{urls["1"]}" srcset="{urls["1"]} 1x, {urls["2"]} 2x, {urls["4"]} 4x" '
            f'title="{escape(emote["name"])}" class="emote">')
        at = emote["end"] + 1
    return html + escape(text[at:])


def test_event(listener: str, text: str = "", channel: dict[str, str] | None = None) -> dict[str, Any]:
    """A Test button's event. A chat message with `text` is sent as the streamer (the channel's name and Twitch
    id), so a widget's chat commands that only the streamer may use can be tried; without text it's a viewer."""
    if listener == "message":
        if str(text).strip() and channel:
            name = channel.get("username") or "Streamer"
            return chat_message(name, name.casefold(), str(text).strip(), "test-message", "broadcaster",
                                channel.get("providerId", ""))
        return chat_message("TestViewer", "testviewer", str(text).strip() or TEST_CHAT, "test-message")
    return dict(TEST_EVENTS[listener][1])


def _tier(data: dict[str, Any]) -> str:
    """Flows have tier 1 / 2 / 3; StreamElements keeps Twitch's "1000" / "2000" / "3000"."""
    try:
        return str(int(data.get("tier", 1)) * 1000)
    except (TypeError, ValueError):
        return "1000"
