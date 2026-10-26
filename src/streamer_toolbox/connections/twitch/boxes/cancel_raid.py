from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox


class CancelRaid(TwitchStreamBox):
    name = "cancel_raid"
    label = "Cancel raid"
    help = "Cancels the raid that is counting down"
    group = "Stream"

    async def run(self) -> None:
        self._allowed("channel:manage:raids")
        await self._helix("DELETE", "raids", params={"broadcaster_id": self._me().user_id})
