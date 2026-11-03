from streamer_toolbox.connections.twitch.boxes.twitch_channel_box import TwitchChannelBox


class SetStreamTitle(TwitchChannelBox):
    name = "set_title"
    label = "Set stream title"
    help = "Changes your stream title"
    hints = {"title": "up to 140 characters"}
    group = "Stream"

    async def run(self, title: str) -> None:
        title = str(title).strip()
        if not title:
            raise ValueError("the title is empty")
        if len(title) > 140:
            raise ValueError(f"Twitch titles are up to 140 characters, this one has {len(title)}")
        await self._helix("PATCH", "channels", params={"broadcaster_id": self._me().user_id}, json={"title": title})
