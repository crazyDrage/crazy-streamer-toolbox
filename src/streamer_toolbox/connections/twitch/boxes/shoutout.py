from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox


class Shoutout(TwitchStreamBox):
    name = "shoutout"
    label = "Shoutout"
    help = "Twitch's own shoutout (/shoutout) for that channel: only while live, at most one every 2 minutes"
    group = "Chat"

    async def run(self, user: str) -> None:
        self._allowed("moderator:manage:shoutouts")
        await self._helix("POST", "chat/shoutouts", params={
            "from_broadcaster_id": self._channel().user_id, "to_broadcaster_id": (await self._user(user))["id"],
            "moderator_id": self._me().user_id})
