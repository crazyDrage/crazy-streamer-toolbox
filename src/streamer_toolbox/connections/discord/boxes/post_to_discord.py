from typing import Any

from streamer_toolbox.connections.discord.boxes.discord_box import DiscordBox, LONGEST


class PostToDiscord(DiscordBox):
    name = "post"
    label = "Post to Discord"
    help = "Writes a message into the Discord channel of the webhook"
    hints = {
"name": "Optional: the name the message is posted under",
"pings": "Yes: @everyone, @here and @names in the text really ping. Leave it off "
"when the text holds a viewer's words"}

    async def run(self, message: str, name: str = "", pings: bool = False) -> None:
        text = str(message).strip()
        if not text:
            raise ValueError("What should be posted?")
        if len(text) > LONGEST:
            raise ValueError(f"Discord takes at most {LONGEST} letters in one message; this has {len(text)}")
        body: dict[str, Any] = {"content": text}
        if str(name).strip():
            body["username"] = str(name).strip()
        if not pings:
            body["allowed_mentions"] = {"parse": []}
        await self._post(body)
