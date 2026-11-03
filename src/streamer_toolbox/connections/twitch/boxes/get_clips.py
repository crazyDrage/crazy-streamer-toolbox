from datetime import timedelta
from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox
from streamer_toolbox.core.data.box_value import to_bool


class GetClips(TwitchStreamBox):
    name = "get_clips"
    label = "Get clips"
    help = "The clips of a channel (yours when the name is empty), most watched first, and one of them picked at " \
           "random. E.g. for a shoutout that plays a clip"
    hints = {"user": "empty = your channel", "count": "how many to look at, up to 100",
             "max_seconds": "0 = any length", "days": "0 = all time",
             "featured": "on: only the clips the channel marked as featured"}
    labels = {"featured": "Only featured"}
    outputs = {"count": "number", "clips": "list", "url": "text", "title": "text",
               "seconds": "number", "thumbnail": "text", "id": "text"}
    group = "Stream"

    async def run(self, user: str = "", count: int = 50, max_seconds: float = 0, days: int = 0,
                  featured: bool = False) -> dict[str, Any]:
        owner = (await self._user(user))["id"] if str(user).strip() else self._me().user_id
        params: dict[str, Any] = {"broadcaster_id": owner, "first": max(1, min(int(count), 100))}
        if to_bool(featured):
            params["is_featured"] = "true"
        if int(days) > 0:
            now = self._now()
            params["started_at"] = (now - timedelta(days=int(days))).strftime("%Y-%m-%dT%H:%M:%SZ")
            params["ended_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        found = (await self._helix("GET", "clips", params=params)).get("data") or []
        clips = [{"id": c["id"], "url": c.get("url", ""), "title": c.get("title", ""),
                  "seconds": c.get("duration", 0), "views": c.get("view_count", 0),
                  "thumbnail": c.get("thumbnail_url", ""), "created": c.get("created_at", "")}
                 for c in found if not float(max_seconds) or c.get("duration", 0) <= float(max_seconds)]
        one = self._pick(clips) if clips else {}
        return {"count": len(clips), "clips": clips, "url": one.get("url", ""), "title": one.get("title", ""),
                "seconds": one.get("seconds", 0), "thumbnail": one.get("thumbnail", ""), "id": one.get("id", "")}
