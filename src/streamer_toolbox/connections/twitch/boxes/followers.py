from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_channel_box import TwitchChannelBox, _first


class Followers(TwitchChannelBox):
    name = "get_followers"
    label = "Followers"
    help = "How many follow you; with a name also whether they follow and since when"
    hints = {"user": "empty = just the count"}
    outputs = {"count": "number", "follows": "yes/no", "since": "text"}
    group = "Viewers"

    async def run(self, user: str = "") -> dict[str, Any]:
        params = {"broadcaster_id": self._me().user_id}
        if str(user).strip():
            params["user_id"] = (await self._user(user))["id"]
        answer = await self._helix("GET", "channels/followers", params=params)
        follow = _first(answer)
        return {"count": answer.get("total", 0), "follows": bool(follow) if "user_id" in params else False,
                "since": follow.get("followed_at", "") if "user_id" in params else ""}
