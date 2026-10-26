from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_channel_box import TwitchChannelBox, _first, _time


class ChannelInfo(TwitchChannelBox):
    name = "get_channel"
    label = "Channel info"
    help = "Your channel now: live or not, viewers, how long you're live, title, category, tags"
    live = True
    outputs = {"live": "yes/no", "viewers": "number", "uptime_seconds": "number", "title": "text",
               "category": "text", "tags": "list"}
    group = "Stream"

    async def run(self) -> dict[str, Any]:
        me = self._me().user_id
        info = _first(await self._helix("GET", "channels", params={"broadcaster_id": me}))
        live = _first(await self._helix("GET", "streams", params={"user_id": me}))
        started = _time(live.get("started_at"))
        return {"live": bool(live), "viewers": live.get("viewer_count", 0),
                "uptime_seconds": round((self._now() - started).total_seconds()) if started else 0,
                "title": info.get("title", ""), "category": info.get("game_name", ""), "tags": info.get("tags", [])}
