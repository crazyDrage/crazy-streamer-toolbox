from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox


class UntimeoutUnban(TwitchStreamBox):
    name = "unban"
    label = "Untimeout / unban"
    help = "Ends a viewer's timeout or ban"
    group = "Viewers"

    async def run(self, user: str) -> None:
        self._allowed("moderator:manage:banned_users")
        await self._helix("DELETE", "moderation/bans",
                          params={**self._as_moderator(), "user_id": (await self._user(user))["id"]})
