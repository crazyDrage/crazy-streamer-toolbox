from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox


class StartRaid(TwitchStreamBox):
    name = "start_raid"
    label = "Start raid"
    help = "Starts a raid to that channel (Twitch runs its 90 second countdown)"
    group = "Stream"

    async def run(self, user: str) -> None:
        self._allowed("channel:manage:raids")
        await self._helix("POST", "raids", params={"from_broadcaster_id": self._me().user_id,
                                                   "to_broadcaster_id": (await self._user(user))["id"]})
