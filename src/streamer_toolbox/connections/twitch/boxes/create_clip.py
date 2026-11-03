from typing import Any

from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox, _first


class CreateClip(TwitchStreamBox):
    name = "create_clip"
    label = "Create clip"
    help = "Clips the last 30 seconds of your stream (only while live); gives the clip's address"
    outputs = {"id": "text", "url": "text",
               "edit_url": "text"}
    group = "Stream"

    async def run(self) -> dict[str, Any]:
        self._allowed("clips:edit")
        clip = _first(await self._helix("POST", "clips", params={"broadcaster_id": self._me().user_id}))
        if not clip:
            raise RuntimeError("Twitch made no clip (clips only work while you're live)")
        return {"id": clip["id"], "url": f"https://clips.twitch.tv/{clip['id']}", "edit_url": clip.get("edit_url", "")}
