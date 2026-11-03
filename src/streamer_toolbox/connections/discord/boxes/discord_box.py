from collections.abc import Awaitable, Callable
from typing import Any

from streamer_toolbox.core.interfaces.box import Box

Post = Callable[[dict[str, Any]], Awaitable[None]]
LONGEST = 2000


class DiscordBox(Box):
    """What the discord boxes share (not a box itself: it has no run).

    Discord's box: a message into the channel the webhook belongs to ("I'm live", a clip's address).
    Names in the text don't ping anyone unless the box says so, so a viewer's words can't call @everyone."""

    def __init__(self, post: Post) -> None:
        self._post = post
