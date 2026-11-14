from typing import Any

from streamer_toolbox.connections.twitch.twitch_picture_lookup import SIZES, TwitchPictureLookup
from streamer_toolbox.core.interfaces.box import Box

TWITCH = "twitch"  # the platform value of Twitch's events (TwitchConnection's PLATFORM)


class TwitchProfilePicture(Box):
    """A Twitch user's profile picture address, for an event's `picture` value (his 11-13: "the flow has to give
    the picture url/path"), e.g. Chat → this box (their user id, the platform) → Send chat (the chat event type's own
    flow has it, his 11-14). Asks Twitch (it keeps its run
    wire, rule 22) through TwitchPictureLookup: once a day per person, many new chatters in one request."""

    name = "profile_picture"
    label = "Twitch profile picture"
    help = ("The address of someone's profile picture. Asks Twitch once a day per person (many at once in one "
            "request); empty when there is none or Twitch can't be reached")
    outputs = {"picture": "text"}
    group = "Viewers"
    hints = {"user": "Their user id (Chat gives user_id) or their name; the id is the safer one",
             "size": "Pixels: 70x70 is enough for a chat",
             "platform": "Chat's platform: someone from another platform (YouTube, ...) gets an empty picture "
                         "without asking Twitch. Empty = always Twitch"}
    options = {"size": lambda: _sizes()}

    def __init__(self, lookup: TwitchPictureLookup) -> None:
        self._lookup = lookup

    async def run(self, user: str, size: str = SIZES[0], platform: str = "") -> dict[str, Any]:
        if str(platform or "").strip().casefold() not in ("", TWITCH):  # a YouTube id is no Twitch user
            return {"picture": ""}
        if not str(user or "").strip():
            raise ValueError("whose picture? (the user is empty)")
        return {"picture": await self._lookup.picture(user, size)}


async def _sizes() -> list[str]:
    return list(SIZES)
