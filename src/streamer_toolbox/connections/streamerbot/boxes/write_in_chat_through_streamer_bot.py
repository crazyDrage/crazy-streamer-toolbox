from streamer_toolbox.connections.streamerbot.boxes.streamerbot_box import (StreamerbotBox, Ask, NEEDS_PASSWORD,
                                                                            PLATFORMS)


class WriteInChatThroughStreamerBot(StreamerbotBox):
    name = "send_chat"
    label = "Write in chat through Streamer.bot"
    help = "Writes in chat through Streamer.bot's own accounts. Streamer.bot only allows it with a password set " \
           "on its WebSocket server"
    hints = {"bot": "Yes: as Streamer.bot's bot account. No: as the streamer"}

    def __init__(self, ask: Ask) -> None:
        super().__init__(ask)
        self.options = {"platform": self.platforms}

    async def run(self, message: str, platform: str = "twitch", bot: bool = True) -> None:
        platform = str(platform).strip().casefold()
        if platform not in PLATFORMS:
            raise ValueError(f"Streamer.bot writes on {', '.join(PLATFORMS)}; not on {platform!r}")
        if not str(message).strip():
            raise ValueError("What should be written?")
        try:
            await self._ask({"request": "SendMessage", "platform": platform, "bot": bool(bot), "internal": False,
                             "message": str(message)})
        except RuntimeError as e:
            if "authentication required" not in str(e).casefold():
                raise
            raise PermissionError(NEEDS_PASSWORD) from None
