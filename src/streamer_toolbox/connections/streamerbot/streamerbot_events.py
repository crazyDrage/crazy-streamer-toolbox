"""What Streamer.bot's websocket says, turned into what the toolbox needs: the answer to its login question
and its events as `streamerbot.event`."""
import base64
import hashlib
from typing import Any

EVENT = "streamerbot.event"


def authentication(password: str, salt: str, challenge: str) -> str:
    """The answer to Streamer.bot's Hello when a password is set (docs.streamer.bot, WebSocket server →
    authentication): base64(sha256(base64(sha256(password + salt)) + challenge))."""
    secret = base64.b64encode(hashlib.sha256((password + salt).encode("utf-8")).digest()).decode("ascii")
    return base64.b64encode(hashlib.sha256((secret + challenge).encode("utf-8")).digest()).decode("ascii")


def streamerbot_event(message: dict[str, Any]) -> dict[str, Any]:
    """{"timeStamp", "event": {"source", "type"}, "data"} as the toolbox's event. Streamer.bot's docs don't
    show what each event's data holds, so `user` and `message` are looked for in the usual places and may
    be empty; `data` always has everything."""
    event = message.get("event") if isinstance(message.get("event"), dict) else {}
    data = message.get("data") if isinstance(message.get("data"), dict) else {}
    said = data.get("message")
    user = data.get("user") if isinstance(data.get("user"), dict) else {}
    who = _first(user, "name", "display", "displayName", "login") or \
        _first(data, "displayName", "userName", "user_name", "username") or \
        (data["user"] if isinstance(data.get("user"), str) else "") or \
        (_first(said, "displayName", "username") if isinstance(said, dict) else "")
    text = said if isinstance(said, str) else _first(said, "message", "text") if isinstance(said, dict) \
        else _first(data, "text")
    return {"source": str(event.get("source") or ""), "type": str(event.get("type") or ""), "user": who,
            "message": text, "data": data}


def _first(holder: dict[str, Any], *keys: str) -> str:
    return next((str(holder[k]) for k in keys if isinstance(holder.get(k), (str, int)) and holder[k] != ""), "")
