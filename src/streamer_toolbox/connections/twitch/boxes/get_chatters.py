from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox


class GetChatters(TwitchStreamBox):
    name = "get_chatters"
    label = "Get chatters"
    help = "Who is in your chat right now: the names and how many"
    live = True
    outputs = {"count": "number", "names": "list"}
    group = "Chat"

    async def run(self) -> dict[str, Any]:
        self._allowed("moderator:read:chatters")
        answer = await self._helix("GET", "chat/chatters", params={**self._as_moderator(), "first": 1000})
        names = [str(c.get("user_name") or c.get("user_login") or "") for c in answer.get("data") or []]
        return {"count": answer.get("total", len(names)), "names": names}
