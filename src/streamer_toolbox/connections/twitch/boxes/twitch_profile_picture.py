from typing import Any

from streamer_toolbox.connections.twitch.twitch_picture_lookup import SIZES, TwitchPictureLookup
from streamer_toolbox.core.interfaces.box import Box


class TwitchProfilePicture(Box):
    """A Twitch user's profile picture address, for an event's `picture` value (his 11-13: "the flow has to give
    the picture url/path"), e.g. Chat → If platform is twitch → this box → Send chat (the chat event type's own
    flow has it, his 11-14). Only Twitch: another platform gets its own box (his round 90: "every platform handles
    it differently"), and the flow shows which way a chat goes (rule 29). Asks Twitch every time (it keeps its run
    wire, rule 22), many chatters in one request; Remembered value keeps the answer (his round 90)."""

    name = "profile_picture"
    label = "Twitch profile picture"
    help = ("The address of a Twitch user's profile picture. Asks Twitch each time (many at once in one "
            "request; Remembered value keeps it); empty when there is none or Twitch can't be reached")
    outputs = {"picture": "text"}
    group = "Viewers"
    labels = {"user_id": "Twitch user id"}
    hints = {"user_id": "Their Twitch user id (Chat gives user_id). Only Twitch's: check the platform before",
             "size": "Pixels: 70x70 is enough for a chat"}
    options = {"size": lambda: _sizes()}

    def __init__(self, lookup: TwitchPictureLookup) -> None:
        self._lookup = lookup

    async def run(self, user_id: str, size: str = SIZES[0]) -> dict[str, Any]:
        if not str(user_id or "").strip():
            raise ValueError("whose picture? (the Twitch user id is empty)")
        return {"picture": await self._lookup.picture(user_id, size)}


async def _sizes() -> list[str]:
    return list(SIZES)
