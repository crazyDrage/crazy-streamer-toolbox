from streamer_toolbox.connections.twitch.boxes.twitch_stream_box import TwitchStreamBox, ANNOUNCEMENT_COLORS, _colors


class Announcement(TwitchStreamBox):
    name = "announce"
    label = "Announcement"
    help = "A highlighted announcement in your chat"
    options = {"color": _colors}
    group = "Chat"

    async def run(self, message: str, color: str = "primary") -> None:
        self._allowed("moderator:manage:announcements")
        message = str(message).strip()
        if not message:
            raise ValueError("the announcement is empty")
        if color not in ANNOUNCEMENT_COLORS:
            raise ValueError(f"the colour is one of {', '.join(ANNOUNCEMENT_COLORS)}")
        await self._helix("POST", "chat/announcements", params=self._as_moderator(),
                          json={"message": message[:500], "color": color})
