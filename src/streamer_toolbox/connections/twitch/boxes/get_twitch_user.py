from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_channel_box import TwitchChannelBox


class GetTwitchUser(TwitchChannelBox):
    name = "get_user"
    label = "Get Twitch user"
    help = "A Twitch user by name: id, name, picture, about, since when, partner / affiliate"
    outputs = {"id": "text", "name": "text", "picture": "text", "about": "text", "created": "text",
               "type": "text"}
    group = "Viewers"

    async def run(self, user: str) -> dict[str, Any]:
        found = await self._user(user)
        return {"id": found["id"], "name": found.get("display_name") or found["login"],
                "picture": found.get("profile_image_url", ""), "about": found.get("description", ""),
                "created": found.get("created_at", ""), "type": found.get("broadcaster_type", "")}
