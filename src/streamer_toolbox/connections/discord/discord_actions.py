from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.actions.action_registry import ActionRegistry

Post = Callable[[dict[str, Any]], Awaitable[None]]  # one message body → the Discord webhook
LONGEST = 2000  # Discord's limit for a message


class DiscordActions:
    """Discord's box: a message into the channel the webhook belongs to ("I'm live", a clip's address).
    Names in the text don't ping anyone unless the box says so, so a viewer's words can't call @everyone."""

    def __init__(self, post: Post) -> None:
        self._post = post

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("discord.post", self.post, "Writes a message into the Discord channel of the webhook",
                    "Post to Discord", hints={
                        "name": "Optional: the name the message is posted under",
                        "pings": "Yes: @everyone, @here and @names in the text really ping. Leave it off "
                                 "when the text holds a viewer's words"})

    async def post(self, message: str, name: str = "", pings: bool = False) -> None:
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
